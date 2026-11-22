# 08: Progress-feedback standard for user waits

**What to build:** A short standards doc at `docs/agents/progress-feedback.md` that the reviewer agent enforces at review time, plus one pointer line in `CLAUDE.md`. The rule: any operation with more than ~2 seconds of user wait streams live progress via the repo's NDJSON streaming pattern (`progress_event`/`result_event`/`error_event` + `streaming_response` on the backend, `fetchWithProgress` on the frontend); task-id polling is reserved for jobs with no meaningful intermediate progress (e.g. image generation, where each image is atomic). The doc spells out the judgement call — which waits deserve streaming versus polling — so the next silent endpoint gets caught at review time, when context pressure is lowest, rather than by the user staring at a spinner. This is a reviewer-enforced doc, not a linter, because the streaming-versus-polling choice is a judgement call. `CLAUDE.md` gains a single line under an appropriate section pointing at the new doc; nothing else in `CLAUDE.md` changes.

**Blocked by:** None (can start immediately).

**Status:** done

- [ ] `docs/agents/progress-feedback.md` states the >~2s rule, the streaming pattern to use, and when task-id polling is acceptable, in a few sentences
- [ ] The doc is written for the reviewer agent to apply at review time (a standard, not a code check)
- [ ] `CLAUDE.md` gains exactly one pointer line to the new doc; no other `CLAUDE.md` content changes
