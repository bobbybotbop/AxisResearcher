# 08: ADR 0003 + glossary updates

**What to build:** The documentation catches up with the new model. A new ADR `docs/adr/0003-distributed-step-status.md` records the decision to replace the centralized Task/Pipeline/StatusStore/PipelineTracker model with distributed per-step status (`StepCard`, local state, direct-call toasts), explicitly superseding ADR 0002 Decisions 1–3 and 6 while noting Decision 5 (determinate progress when counts are known) survives. `GLOSSARY.md` entries for Task, Pipeline, Status Store, and PipelineTracker are updated to describe the new model (or removed if the concept no longer exists), and a StepCard entry is added if it earns a domain term. Glossary stays free of implementation detail.

**Blocked by:** 07 (Contract — delete StatusStore, PipelineTracker, ProgressIndicator)

**Status:** done

- [ ] ADR 0003 exists, follows the repo's ADR format, and states what it supersedes in ADR 0002 and why the trade-off was made
- [ ] Glossary entries match the shipped reality; no entry describes a deleted component as current
- [ ] ADR 0002 is annotated (not rewritten) pointing to 0003 for the superseded decisions
