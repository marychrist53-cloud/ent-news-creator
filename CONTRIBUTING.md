# Contributing

Thanks for considering a contribution. Keep changes focused, preserve private-chat draft isolation, and do not add credentials or production data.

## Development checks

Use Python 3.12, install `requirements.txt` and `requirements-dev.txt`, then run:

```powershell
.venv\Scripts\python.exe -m unittest discover -v
.venv\Scripts\ruff.exe check bot.py entnews tests
python ops/check-secrets.py
```

Tests must remain offline: do not require live Telegram messages, provider credentials, or paid API requests. Add regression coverage for changes to access checks, persistence, and provider behavior.

## Security and data

- Never submit `.env`, tokens, API keys, SSH material, live SQLite databases, logs, or backups.
- Keep `/status` and `/setkey` operator-only.
- Preserve private-chat-only access and per-chat draft filtering.
- Do not include user message text or personal chat data in diagnostic logs.

## Pull requests

Explain the user-facing change, the checks run, and any configuration or migration impact. A project license has not been selected yet; do not assume permission to redistribute or relicense it.
