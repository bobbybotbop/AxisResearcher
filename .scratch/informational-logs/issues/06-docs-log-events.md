# 06: Docs — log event reference

**What to build:** The architecture doc's activity-log section lists all seven event types (`draft_created`, `draft_completed`, `upload`, `import`, `restock`, `sync_active`, `sync_startup`) with a one-line description of each payload, replacing the current list that omits the sync events and predates the enriched payloads.

**Blocked by:** 02, 03, 04 (the sync/import payload shapes must be final before they are documented)

**Status:** resolved

- [ ] `docs/agents/architecture.md` documents all seven event types with their payload fields.
- [ ] The documented payloads match what the backend actually writes after tickets 02–04.
