# Changelog

## 1.2.0

- Opened ordinary bot features to users in private chats while keeping provider configuration operator-only.
- Added per-chat draft ownership, private retrieval, and configurable per-user/global generation caps.
- Added private-chat-only handling, operator-scoped Telegram commands, and startup without a required operator ID.
- Added portfolio overview and project roadmap documentation.

## 1.1.0

- Persisted chats, story snapshots, message bindings, health state, and drafts in SQLite.
- Added safe import from legacy JSON and retained automatic database backups.
- Kept story actions attached to the story shown, and preserved search/date selection across refreshes.
- Added provider timeouts, limited retries, health reporting, and secret-redacted logging.
- Distinguished published reporting from TMDB catalogue metadata and filtered stale or out-of-range results.
- Added Burmese draft style controls, bounded rewrites, image attribution, CI, and offline regression tests.

## 1.0.0

- Initial private Telegram entertainment news and Burmese draft bot.
