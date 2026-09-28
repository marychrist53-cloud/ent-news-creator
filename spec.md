# Project specification

**Project:** Entertainment News Creator Bot
**Version:** 1.2.0 (public-access preparation)
**Runtime:** Python 3.12+, Telegram long-polling bot
**Primary language for generated posts:** Burmese

## Purpose

The bot gives public Telegram users a compact entertainment-news and film/TV release feed in private chats. Users can inspect source stories, create Burmese drafts for human review, adjust length and tone, rewrite drafts, find relevant images, and revisit their own saved drafts.

## User and access model

- Any Telegram user can use ordinary bot features in a private chat. Group chats are rejected so preferences and generated drafts are not shared with other group members.
- `ADMIN_TELEGRAM_ID` is optional. If configured, only that user can use `/status` and `/setkey`; without it, provider credentials must be configured through environment variables.
- Public users can create up to five AI drafts per day, with a 30-second per-chat cooldown. A global default cap of 100 drafts per day bounds shared provider usage. These controls are configurable.
- Saved drafts include their owning Telegram chat ID and are filtered on retrieval. Legacy drafts without an owner remain visible to the configured operator only.
- `/setkey` is operator-only, accepts private-chat commands only, deletes the submitted Telegram message when possible, and never displays key values. `/status` is operator-only.
- The service runs one long-polling process. Do not run a second local polling process with the same Telegram token.

## Commands

| Command | Behavior |
| --- | --- |
| `/topics`, `/menu`, `/news` | Choose an entertainment industry and focus. |
| `/topic <query>` | Fetch a custom news topic. |
| `/search <query>` | Search current news and film/TV catalogue records. |
| `/upcoming <date-or-month>` | Find TMDB releases in the requested date range. |
| `/refresh` | Repeat the last topic, search, or date selection. |
| `/create` | Reply to a saved story or use its button to generate a Burmese draft. |
| `/photo` | Reply to a story, use its button, or search by keywords. |
| `/style short|detailed [editorial|neutral|friendly]` | Set per-chat writing preferences. |
| `/rewrite <instructions>` | Rewrite the last draft or a replied-to story. |
| `/posts` | Browse saved drafts by page; `/posts <id>` opens a draft. |
| `/status` | Operator only: show configured-key presence and provider health, never key values. |
| `/setkey <provider> <key>` | Operator only: configure NewsAPI, Gemini, Pexels, or TMDB in private chat. |
| `/start`, `/help`, `/commands` | Show usage and Telegram command menu. |

## Content and provider behavior

- Google News RSS and configured entertainment publisher feeds require no key.
- NewsAPI is optional and supplies reported articles.
- TMDB is optional and supplies catalogue and release-date metadata. TMDB records are labelled as title information and must not be described as breaking news or evidence of popularity, critical response, or box-office results.
- Gemini is optional. Prompts ask for fluent Burmese composed as original entertainment copy, with an extended editorial structure for detailed drafts. `GEMINI_MODEL` is tried first, then `GEMINI_FALLBACK_MODEL` if unavailable or quota-limited. TMDB catalogue details are attributed as such, and prompts must not add unsupported plot details or audience reactions. Generated copy is stored as a draft and explicitly asks the operator to review facts. Failed generation returns a source summary marked as not a completed draft; it is not saved as generated copy.
- Pexels, Openverse, and Wikimedia Commons are optional image sources. Results retain creator, source, and license details when supplied. Keyword results are labelled for subject verification. The bot does not determine whether a particular reuse is permitted.
- Provider requests have timeouts, bounded concurrency, limited retries, independent error handling, and visible health state.
- Reported news needs a parseable publication time within `MAX_NEWS_AGE_DAYS` (default seven) and may not be future dated. A “today” release needs a matching local date and explicit release wording. TMDB “today” results must match the release date.

## State and durability

- SQLite stores per-chat selection and style, story snapshots, Telegram message-to-story bindings, cached results, drafts, and health status.
- A button identifies the story snapshot it was created for. Reply actions resolve using both chat and message IDs; they do not silently use the current result number.
- On first startup, `news.json` and `posts.json` are validated and imported together. Original files are retained. An invalid legacy file stops startup without marking the import complete.
- Daily SQLite backups are stored beside the database under `backups/`; the latest seven are retained.
- `BOT_DATA_DIR` selects the writable data directory. The default is `data/` under the project directory.

## Runtime configuration

See `.env.example` for the complete list and defaults. The service requires `TELEGRAM_BOT_TOKEN`; `ADMIN_TELEGRAM_ID` is optional. Provider APIs can be omitted, though some features will then be unavailable. Gemini defaults to `gemini-3.5-flash` with `gemini-3.5-flash-lite` as fallback. Public draft limits are configurable with `MAX_PUBLIC_DRAFTS_PER_DAY`, `MAX_PUBLIC_DRAFTS_GLOBAL_PER_DAY`, and `PUBLIC_DRAFT_COOLDOWN_SECONDS`. `ENABLE_ADMIN_ALERTS=true` enables Telegram alerts after repeated provider or backup failures. `BOT_ENV_FILE` and `BOT_DATA_DIR` support service deployments with separate configuration and data paths.

## Service lifecycle and security

- The process owns one shared asynchronous HTTP client and closes it during shutdown.
- Logs suppress HTTP transport request details and redact configured secrets and Telegram token patterns.
- The production host runs the process under a dedicated unprivileged service account with systemd restart and filesystem protections.
- Public access consumes the operator's configured provider quotas. Configure provider spending limits and monitor usage before sharing the bot widely.
- Keep tokens, local `.env`, SQLite databases, backups, logs, and legacy JSON data out of version control and release archives.
- Rotate any credential that has appeared in a public or shared location.

## Verification and release

- Offline regression tests use Python's standard `unittest` runner and mocked HTTP transports.
- Ruff checks syntax-level errors, undefined names, and import ordering.
- CI runs the same checks on Linux and Windows with Python 3.12.
- A GitHub repository can be prepared from the curated source files in this workspace. A public license must be selected by the owner before public distribution; none is granted by this specification.
