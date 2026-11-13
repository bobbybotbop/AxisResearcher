# 01: Reject .amf in the download step

**What to build:** `.amf` is no longer a supported 3D format anywhere in the pipeline. It is removed from the preferred 3D extensions ranking, and if a Step 3 download resolves to an `.amf` file (e.g. it is the only/best file in a zip), the download step fails with a clear, user-visible ".amf is not supported" error instead of handing the user an unusable file.

**Blocked by:** None (can start immediately).

**Status:** ready-for-agent

- [ ] `.amf` no longer appears in the preferred 3D extensions
- [ ] A Step 3 download that would yield an `.amf` file errors with a message explicitly stating `.amf` is not supported
- [ ] Downloads of all other formats behave exactly as before
- [ ] `python -m pytest tests/` passes
