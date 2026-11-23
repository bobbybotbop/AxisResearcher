# 06: Data Browser + Logs loading bars

**What to build:** Data Browser and Logs show a thin top loading bar while their tables load, instead of the current spinner or nothing. Both report through the Status Store.

**Blocked by:** 01 (Status Store + Task/Pipeline model)

**Status:** done

- [ ] Data Browser shows a top loading bar while the table loads
- [ ] Logs shows a top loading bar while entries load
- [ ] Both report through the store
- [ ] `cd frontend && npm run build` passes; `python -m pytest tests/` passes
