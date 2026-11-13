# 06: Performance tuning + hardening

**What to build:** The render pipeline is tuned and hardened to the spec's performance contract. Cycles sample count, adaptive sampling, and OIDN denoising are tuned so a 1024x1024 render of a typical model completes in the 10–25 second band on the Ryzen 9 5900HS (30s soft target), measured with an actual render. A 90-second hard kill terminates a hung Blender process and surfaces a friendly timeout error. Error surfaces are verified end to end: missing Blender, failed conversion, unsupported format, timeout — each produces a clear panel message. Final verification: full frontend build and test suite pass, and the complete flow (Step 3 download → Step 4 preview → adjust settings → Render → image + download) works end to end.

**Blocked by:** 03 (Live preview + Camera Intent), 04 (Format normalization), 05 (Controls panel + persisted Render Settings).

**Status:** ready-for-agent

- [ ] A measured 1024x1024 render of a real downloaded model completes within the 10–25s band on this machine
- [ ] A Blender process exceeding 90s is killed and reported as a friendly timeout error
- [ ] Each failure mode (missing Blender, conversion failure, unsupported format, timeout) shows a clear panel error
- [ ] Full flow verified end to end; `cd frontend && npm run build` passes; `python -m pytest tests/` passes
