# Security policy

## Supported version

Security fixes target the latest maintained version on the default branch.

## Reporting a vulnerability

Do not open a public issue containing a token, password, private key, personal data, or an exploitable production detail. Use GitHub's private vulnerability reporting for this repository when enabled, or contact the repository owner privately.

If a credential is exposed, revoke or rotate it with its provider, update the private runtime configuration, and check that it does not remain in logs, chat history, or Git history.

## Secrets and production state

Never commit `.env`, API keys, bot tokens, SSH keys, production SQLite data, backups, or logs. Review image source and license information before reuse.

The bot accepts public users only in private chats. Drafts are stored with their owning Telegram chat ID and are returned only to that owner. `/status` and `/setkey` require the configured `ADMIN_TELEGRAM_ID`. Public draft generation is limited per chat and has a cooldown. Keep public API quotas and provider spending limits enabled.
