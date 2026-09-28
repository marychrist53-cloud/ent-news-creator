#!/usr/bin/env bash
set -euo pipefail

APP_DIR=/opt/ent-news-bot
ENV_FILE="$APP_DIR/.env"
SERVICE=ent-news-bot.service

if [[ $EUID -ne 0 ]]; then
    echo "Run this script as root." >&2
    exit 1
fi

read -r -s -p "Paste the replacement Telegram bot token: " token
printf '\n'

if [[ ! $token =~ ^[0-9]+:[A-Za-z0-9_-]{20,}$ ]]; then
    unset token
    echo "Token format is invalid; no files were changed." >&2
    exit 1
fi

if ! TELEGRAM_BOT_TOKEN="$token" /opt/ent-news-bot/.venv/bin/python - <<'PY'
import json
import os
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

token = os.environ["TELEGRAM_BOT_TOKEN"]
url = f"https://api.telegram.org/bot{token}/getMe"
try:
    with urllib.request.urlopen(url, timeout=15) as response:
        payload = json.load(response)
except Exception:
    print("Telegram validation failed; the saved configuration was not changed.")
    raise SystemExit(1)

if not payload.get("ok"):
    print("Telegram rejected the replacement token; the saved configuration was not changed.")
    raise SystemExit(1)

env_file = Path("/opt/ent-news-bot/.env")
lines = env_file.read_text(encoding="utf-8").splitlines()
updated = []
replaced = False
for line in lines:
    if line.split("=", 1)[0].strip() == "TELEGRAM_BOT_TOKEN":
        if not replaced:
            updated.append(f"TELEGRAM_BOT_TOKEN={token}")
            replaced = True
    else:
        updated.append(line)
if not replaced:
    updated.append(f"TELEGRAM_BOT_TOKEN={token}")

fd, temporary = tempfile.mkstemp(prefix=".env.", dir=env_file.parent)
try:
    os.fchmod(fd, 0o600)
    os.fchown(fd, env_file.stat().st_uid, env_file.stat().st_gid)
    with os.fdopen(fd, "w", encoding="utf-8") as output:
        output.write("\n".join(updated).rstrip() + "\n")
    os.replace(temporary, env_file)
except Exception:
    try:
        os.unlink(temporary)
    except OSError:
        pass
    print("Could not securely update the environment file.")
    raise SystemExit(1)
PY
then
    unset token
    exit 1
fi

unset token
systemctl restart "$SERVICE"
for _ in {1..10}; do
    if systemctl is-active --quiet "$SERVICE"; then
        echo "Token validated and saved; $SERVICE is active."
        exit 0
    fi
    sleep 1
done

echo "Token was saved, but $SERVICE did not become active. Check: journalctl -u $SERVICE" >&2
exit 1
