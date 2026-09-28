# Entertainment News Creator Bot

A public Telegram bot for entertainment news and film/TV releases. It creates Burmese article drafts, searches for attributed images, and keeps each user's drafts private.

## Features

- Industry and focus menus for film and television topics
- Google News, publisher RSS, optional NewsAPI and TMDB results
- Per-chat selections with story-specific Create and Photos buttons
- Optional Gemini writing with short or detailed length and three tones
- Image results from optional Pexels, Openverse, and Wikimedia Commons with source and license details when available
- SQLite state, first-start import of legacy JSON, and daily retained backups
- Provider health, bounded network retries, and optional failure alerts
- Public private-chat access with operator-only credential management
- Per-user draft isolation, usage limits, and secret-safe status and logs

TMDB data is catalogue metadata, not independent reporting. Generated text is a draft and needs a human fact check. Image search metadata helps identify the source; the operator is responsible for reviewing image context and reuse requirements.

## Requirements

- Python 3.12
- A Telegram bot token
- Optional numeric Telegram user ID for operator commands
- Optional API credentials for NewsAPI, Gemini, TMDB, and Pexels

## Local setup

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt -r requirements-dev.txt
Copy-Item .env.example .env
```

Edit `.env` with your Telegram bot token. Add your numeric `ADMIN_TELEGRAM_ID` if you want private operator commands for `/status` and `/setkey`. Keep `.env` private. Then run:

```powershell
.venv\Scripts\python bot.py
```

On Linux or macOS, activate `.venv`, install the same requirements, copy `.env.example` to `.env`, and run `python bot.py`.

The bot requires only `TELEGRAM_BOT_TOKEN` at startup. Any Telegram user can use it in a private chat. Set `ADMIN_TELEGRAM_ID` to enable operator-only key configuration and health status; if omitted, configure provider keys through `.env`. Use only one running polling process for a bot token.

## Commands

| Command | Description |
| --- | --- |
| `/topics` | Choose an industry and focus. |
| `/topic <query>` | Load a custom topic. |
| `/search <keywords>` | Search news and title records. |
| `/upcoming <date-or-month>` | Find releases for a date or month. |
| `/refresh` | Refresh the current selection. |
| `/create` | Reply to a story or use its Create button. |
| `/photo` | Reply to a story, use Photos, or search keywords. |
| `/style short|detailed [editorial|neutral|friendly]` | Set writing preferences. |
| `/rewrite <instructions>` | Rewrite the latest draft or a replied-to story. |
| `/posts` | Browse drafts; `/posts <id>` opens one. |
| `/status` | Operator only: show provider health and key presence. |
| `/setkey <provider> <key>` | Operator only: set `newsapi`, `gemini`, `tmdb`, or `pexels`. |

See `/help` for examples and [spec.md](spec.md) for behavior and operational details.

## Configuration

`.env.example` lists all supported settings. `TELEGRAM_BOT_TOKEN` is required; `ADMIN_TELEGRAM_ID` is optional and enables operator-only commands. Optional API keys enable their providers. Public users can create up to five drafts per day, with a 30-second cooldown; all public users share a global default cap of 100 drafts per day. Configure `MAX_PUBLIC_DRAFTS_PER_DAY`, `MAX_PUBLIC_DRAFTS_GLOBAL_PER_DAY`, and `PUBLIC_DRAFT_COOLDOWN_SECONDS` to change those limits. Set `ENABLE_ADMIN_ALERTS=true` to message the operator after repeated failures.

Gemini uses `gemini-3.5-flash` first for Burmese draft generation and falls back to `gemini-3.5-flash-lite` if that model is unavailable or quota-limited. Configure `GEMINI_MODEL` and `GEMINI_FALLBACK_MODEL` for your Google AI Studio project as needed.

By default, SQLite state is in `data/bot.sqlite3`. Each user's preferences and drafts are isolated by private chat. Set `BOT_DATA_DIR` to move state outside the source checkout. Set `BOT_ENV_FILE` to load configuration from another path. If `news.json` and `posts.json` exist beside `bot.py` on first startup, the bot imports their contents transactionally and leaves the original files in place.

## Tests and checks

```powershell
.venv\Scripts\python -m unittest discover -v
.venv\Scripts\ruff check bot.py entnews tests
```

Tests use temporary databases and mocked transports. They do not poll Telegram, invoke paid services, or need production credentials.

## Production deployment

Use a dedicated service account, private environment file, writable data directory, systemd restart policy, and backups. See [ops/README.md](ops/README.md) for the VPS release and rollback procedure. Do not copy a local `.env`, database, JSON cache, or backup over production data.

## GitHub readiness

The repository excludes secrets, live state, virtual environments, and build artifacts. CI runs offline checks on Linux and Windows. See [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md), [ROADMAP.md](ROADMAP.md), and [CONTRIBUTING.md](CONTRIBUTING.md) for portfolio and contributor documentation. No `LICENSE` file is included; choose a license before accepting contributions or granting reuse rights.
