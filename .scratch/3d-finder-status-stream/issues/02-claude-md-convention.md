# 02: Document the streaming-progress convention in CLAUDE.md

**What to build:** A short convention note in `CLAUDE.md` so future work follows this pattern automatically: long-running endpoints must stream NDJSON progress via the shared `streaming_response`/`progress_event` helpers; frontends consume via `fetchWithProgress`; progress messages are non-technical user-facing text; numeric progress is shown only when the data source provides real counts.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] `CLAUDE.md` contains the convention note in a sensible section
- [ ] The note covers all four rules above in a few sentences, no more
- [ ] No other content in `CLAUDE.md` is changed
