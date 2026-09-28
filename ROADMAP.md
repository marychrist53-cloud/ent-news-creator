# Project roadmap

This roadmap separates shipped capabilities from work that would make the bot safer to share, easier to maintain, and stronger as a portfolio project.

## Completed foundation

- [x] Telegram command and button flow for topics, search, releases, drafts, rewrites, and photos.
- [x] News discovery from Google News and entertainment publisher feeds, with optional NewsAPI and TMDB.
- [x] Gemini-backed Burmese draft generation with source-aware prompts and a model fallback.
- [x] SQLite persistence for per-chat preferences, snapshots, drafts, and health state.
- [x] Legacy JSON import, daily backups, secret redaction, systemd deployment notes, and cross-platform CI.

## Public sharing and security

- [x] Allow ordinary users to use the bot in private chats without an operator ID.
- [x] Keep `/status` and `/setkey` operator-only.
- [x] Filter saved drafts by owning chat and preserve operator access to legacy drafts.
- [x] Add configurable per-chat daily generation and cooldown controls, plus a shared daily cap.
- [x] Reject group-chat use to keep preferences and drafts private.
- [ ] Choose and add a project license before accepting contributions or reuse.
- [ ] Add a public-facing bot username and a short privacy notice to the README after confirming the public bot profile.
- [ ] Review actual provider spending and quota limits before advertising the bot widely.
- [ ] Verify public `/start`, `/topics`, `/create`, `/posts`, and admin command behavior using two separate Telegram accounts.

## Burmese writing quality

- [ ] Build a small, reviewed set of Burmese source-and-draft examples covering news reports, catalogue summaries, and upcoming releases.
- [ ] Evaluate outputs for fluency, factual support, proper names, paragraph structure, and repetitive phrasing.
- [ ] Let the operator adjust article length, house style, and headline behavior without editing source code.
- [ ] Track the model used for each saved draft so editorial feedback can be compared across models.
- [ ] Add a review checklist or fact/source view beside each generated draft.

## Reliability and operations

- [ ] Add a configurable provider-wide circuit breaker for repeated quota and server failures.
- [ ] Add tests for Telegram access control, public quota boundaries, and draft ownership across multiple users.
- [ ] Add a documented restore drill that verifies both database restoration and service recovery.
- [ ] Add lightweight aggregate metrics for request counts, provider failures, and generation fallback usage without storing message content.
- [ ] Review and refresh broken RSS endpoints and guard NewsAPI query length before requests.
- [ ] Define log and database retention windows appropriate for a public service.

## Portfolio presentation

- [ ] Capture redacted screenshots of public commands, a source-backed story, a generated Burmese draft, and photo attribution.
- [ ] Add a system overview diagram and a short demo video or GIF that contains no credentials or private chats.
- [ ] Publish a public repository only after checking staged files and Git history for secrets and production data.
- [ ] Add contribution instructions and a license decision.
- [ ] Document the deployment process with sanitized configuration examples and no server addresses.

## Scale-up path

If usage outgrows one VPS, move from single-process polling and local SQLite to webhook delivery, a managed database, background job workers, and centralized monitoring. Make that migration only when observed traffic or reliability needs justify the extra operational complexity.
