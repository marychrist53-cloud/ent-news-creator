# Production operations

Run the bot as a dedicated non-login user with Python 3.12, a root-owned code tree, a private environment file, and a separate writable state directory. Restrict the environment file to the service account. Keep SSH key access private and disable password login when key access is verified. Public users should use the bot in private chats; configure the generation limits and provider spending caps before sharing it broadly.

## Release checklist

1. Build and verify the release locally: install `requirements.txt`, run Ruff, and run the offline unit tests.
2. Copy only `bot.py`, `entnews/`, and the pinned runtime requirements to a staging directory. Never upload `.env`, `data/`, `backups/`, local `news.json`, or `posts.json`.
3. Check the staged files and Python dependencies before stopping the service.
4. Stop the service briefly and back up the live code, private environment, and state database into a root-readable backup directory. Keep permissions restrictive.
5. Install staged code. Preserve the production environment, database, and service unit. The SQLite importer reads legacy JSON once if no previous import marker exists.
6. Start the service. Check `systemctl is-active`, the new process journal for errors, operator `/status`, public `/start` access, and the first scheduled fetch.
7. If startup or migration fails, stop the service, restore the previous code and database backup, and start the previous version.

SQLite backups are created daily by the bot in `BOT_DATA_DIR/backups/`; seven are retained. Also keep a separate off-host backup for disaster recovery.

## Token rotation

The `update-telegram-token.sh` helper prompts without echo, validates the token with Telegram, atomically updates the private environment file, and restarts the service. Run it only on a host with the expected installation path. Avoid passing tokens in shell arguments, command history, chat, or logs.

## Service health

`/status` reports last provider success and consecutive empty/error results. Set `ENABLE_ADMIN_ALERTS=true` in the private environment file to send an alert after three repeated failures. Review service logs with `journalctl -u ent-news-bot.service`; the application redacts configured secrets and suppresses HTTP client request URL logs.
