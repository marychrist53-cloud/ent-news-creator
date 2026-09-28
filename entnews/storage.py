"""Transactional state with a one-time, non-destructive legacy JSON import."""

import hashlib
import json
import os
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as output:
            output.write(text)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def story_id(article: dict) -> str:
    identity = article.get("url") or article.get("title")
    if not identity:
        raise ValueError("A story needs a URL or title")
    snapshot = json.dumps(article, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(snapshot.encode()).hexdigest()[:24]


class Store:
    def __init__(self, path: Path, legacy_dir: Path | None = None):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS stories (id TEXT PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS messages (
                    chat_id INTEGER, message_id INTEGER, story_id TEXT NOT NULL,
                    PRIMARY KEY(chat_id, message_id));
                CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL);
            """)
        if legacy_dir:
            self.migrate(legacy_dir)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        try:
            db.execute("PRAGMA busy_timeout=15000")
            with db:
                yield db
        finally:
            db.close()

    def migrate(self, directory: Path) -> None:
        with self.connect() as db:
            if db.execute("SELECT 1 FROM meta WHERE key='legacy_import'").fetchone():
                return
            # Parse everything before committing. Bad files must never become empty state.
            parsed = {}
            for name in ("news", "posts"):
                path = directory / f"{name}.json"
                data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
                if not isinstance(data, list) or any(not isinstance(x, dict) for x in data):
                    raise ValueError(
                        f"Invalid legacy {name}.json; repair or restore it before starting"
                    )
                parsed[name] = data
            for post in parsed["posts"]:
                pid = post.get("id")
                if not isinstance(pid, int) or pid < 1:
                    raise ValueError("Legacy posts need positive integer IDs")
                db.execute(
                    "INSERT INTO posts(id,payload) VALUES (?,?)",
                    (pid, json.dumps(post, ensure_ascii=False)),
                )
            db.execute(
                "INSERT INTO meta VALUES ('news',?)",
                (json.dumps(parsed["news"], ensure_ascii=False),),
            )
            db.execute("INSERT INTO meta VALUES ('legacy_import','1')")

    def get_meta(self, key, default=None):
        with self.connect() as db:
            row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set_meta(self, key, value):
        with self.connect() as db:
            db.execute(
                "INSERT OR REPLACE INTO meta VALUES (?,?)",
                (key, json.dumps(value, ensure_ascii=False)),
            )

    def put_story(self, article: dict) -> str:
        sid = story_id(article)
        with self.connect() as db:
            # A button references the first saved snapshot of that source story.
            db.execute(
                "INSERT OR IGNORE INTO stories VALUES (?,?)",
                (sid, json.dumps(article, ensure_ascii=False)),
            )
        return sid

    def get_story(self, sid: str) -> dict | None:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM stories WHERE id=?", (sid,)).fetchone()
        return json.loads(row[0]) if row else None

    def bind_message(self, chat_id: int, message_id: int, article: dict):
        sid = self.put_story(article)
        with self.connect() as db:
            db.execute("INSERT OR REPLACE INTO messages VALUES (?,?,?)", (chat_id, message_id, sid))

    def from_message(self, chat_id: int, message_id: int):
        with self.connect() as db:
            row = db.execute(
                "SELECT s.payload FROM messages m JOIN stories s ON s.id=m.story_id WHERE m.chat_id=? AND m.message_id=?",
                (chat_id, message_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def get_chat(self, chat_id: int) -> dict:
        with self.connect() as db:
            row = db.execute("SELECT payload FROM chats WHERE id=?", (chat_id,)).fetchone()
        return json.loads(row[0]) if row else {}

    def update_chat(self, chat_id: int, **changes) -> dict:
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload FROM chats WHERE id=?", (chat_id,)).fetchone()
            state = json.loads(row[0]) if row else {}
            state.update(changes)
            db.execute(
                "INSERT OR REPLACE INTO chats VALUES (?,?)",
                (chat_id, json.dumps(state, ensure_ascii=False)),
            )
        return state

    def add_post(self, post: dict) -> dict:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO posts(payload) VALUES (?)", (json.dumps(post, ensure_ascii=False),)
            )
            return {**post, "id": cursor.lastrowid}

    def posts(
        self, owner_chat_id: int | None = None, include_unowned: bool = False
    ) -> list[dict]:
        with self.connect() as db:
            posts = [
                {**json.loads(payload), "id": pid}
                for pid, payload in db.execute("SELECT id,payload FROM posts ORDER BY id")
            ]
        if owner_chat_id is not None:
            posts = [
                post
                for post in posts
                if post.get("owner_chat_id") == owner_chat_id
                or (include_unowned and post.get("owner_chat_id") is None)
            ]
        return posts

    def backup(self, directory: Path, keep: int = 7) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        destination = directory / (
            "bot-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".sqlite3"
        )
        with self.connect() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
            finally:
                target.close()
        for old in sorted(directory.glob("bot-*.sqlite3"), reverse=True)[keep:]:
            old.unlink()
        return destination
