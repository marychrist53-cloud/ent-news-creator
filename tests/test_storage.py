import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from entnews.storage import Store, atomic_write, story_id


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "state.sqlite3"

    def test_legacy_import_preserves_ids_and_is_idempotent(self):
        (self.root / "posts.json").write_text(
            json.dumps([{"id": 8, "text": "မြန်မာ"}]), encoding="utf-8"
        )
        (self.root / "news.json").write_text('[{"title":"Original"}]')
        store = Store(self.path, self.root)
        self.assertEqual(store.posts()[0]["id"], 8)
        self.assertEqual(store.add_post({"text": "Next"})["id"], 9)
        reopened = Store(self.path, self.root)
        self.assertEqual(len(reopened.posts()), 2)
        self.assertTrue((self.root / "posts.json").exists())
        self.assertEqual(reopened.get_meta("news")[0]["title"], "Original")

    def test_corruption_does_not_become_empty_import(self):
        (self.root / "posts.json").write_text("broken")
        with self.assertRaises(ValueError):
            Store(self.path, self.root)
        self.assertIsNone(Store(self.path).get_meta("legacy_import"))

    def test_invalid_id_rolls_back_entire_import(self):
        (self.root / "posts.json").write_text('[{"id":2},{"id":0}]')
        with self.assertRaises(ValueError):
            Store(self.path, self.root)
        self.assertEqual(Store(self.path).posts(), [])

    def test_concurrent_post_ids_are_unique(self):
        store = Store(self.path)
        with ThreadPoolExecutor(max_workers=4) as pool:
            posts = list(pool.map(lambda n: store.add_post({"text": str(n)}), range(32)))
        self.assertEqual(len({p["id"] for p in posts}), 32)
        self.assertEqual(len(store.posts()), 32)

    def test_saved_posts_can_be_filtered_by_owner_without_leaking_legacy_posts(self):
        store = Store(self.path)
        store.add_post({"owner_chat_id": 101, "text": "first user's draft"})
        store.add_post({"owner_chat_id": 202, "text": "second user's draft"})
        store.add_post({"text": "legacy draft"})
        self.assertEqual(
            [post["text"] for post in store.posts(owner_chat_id=101)],
            ["first user's draft"],
        )
        self.assertEqual(
            [post["text"] for post in store.posts(owner_chat_id=101, include_unowned=True)],
            ["first user's draft", "legacy draft"],
        )

    def test_snapshots_and_message_bindings_survive_restart(self):
        store = Store(self.path)
        old = {"url": "https://example.org/story", "title": "Original"}
        new = {**old, "title": "Changed"}
        first = store.put_story(old)
        second = store.put_story(new)
        self.assertNotEqual(first, second)
        self.assertEqual(first, story_id(dict(reversed(list(old.items())))))
        store.bind_message(1, 7, old)
        store.bind_message(2, 7, new)
        store = Store(self.path)
        self.assertEqual(store.from_message(1, 7), old)
        self.assertEqual(store.from_message(2, 7), new)
        self.assertIsNone(store.from_message(3, 7))

    def test_chat_updates_preserve_other_fields(self):
        store = Store(self.path)
        store.update_chat(1, articles=[{"title": "A"}])
        store.update_chat(1, style={"length": "short"})
        self.assertEqual(store.get_chat(1)["articles"][0]["title"], "A")
        self.assertEqual(store.get_chat(2), {})

    def test_backup_restores_and_retains_only_requested_count(self):
        store = Store(self.path)
        store.add_post({"text": "Saved"})
        for _ in range(4):
            backup = store.backup(self.root / "backups", keep=2)
        self.assertEqual(len(list((self.root / "backups").glob("bot-*.sqlite3"))), 2)
        self.assertEqual(Store(backup).posts()[0]["text"], "Saved")

    def test_atomic_write_replaces_complete_file(self):
        path = self.root / "config"
        atomic_write(path, "before")
        atomic_write(path, "after\n")
        self.assertEqual(path.read_text(), "after\n")
        self.assertEqual(list(self.root.glob(".config.*")), [])
