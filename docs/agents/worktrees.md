# Worktrees: parallel orchestrated builds

`/implement-spec` builds each spec in a dedicated **orchestrator worktree** at
`.worktrees/<spec-name>` (integration branch), with one worktree per ticket at
`.worktrees/<spec>-<ticket>`. The user's main checkout is never touched, so multiple
sessions can each run their own orchestrator + subagents concurrently.

## Dev environments per worktree

Every worktree can run its own full dev stack (Flask + Vite) side by side with the
main checkout and other worktrees:

- Ports come from `AXIS_FRONTEND_PORT` / `AXIS_BACKEND_PORT` in the worktree's `.env`
  (defaults: 4000/5000, which the main checkout keeps).
- The port registry lives at `.scratch/worktree-ports.json` **in the main checkout** —
  it is the source of truth for which worktree owns which ports.
- `npm run dev` bootstraps itself on first run in any worktree
  (`scripts/ensure_dev_ports.py`): copies `.env`, allocates a unique port pair,
  junctions `.venv`, installs frontend deps, then prints the worktree's URL.
- `npm run force-close` only kills the ports of the checkout it runs in — it can never
  kill another worktree's or the main checkout's dev servers.
- Each worktree has its own `axis.db` (gitignored); pass `--with-db` at bootstrap time
  to seed it from the main checkout's database.

## Orchestrator vs ticket worktrees

- **Orchestrator worktrees** (`.worktrees/<spec-name>`): bootstrap them (the
  `implement-spec` skill does this right after creation) so they can run the app
  end-to-end to confirm everything works.
- **Ticket worktrees** (`.worktrees/<spec>-<ticket>`): tests only. Never bootstrap,
  never run dev servers in them.

## Commands

```
./wt boot <spec>     # bootstrap .worktrees/<spec> (usually automatic)
./wt list            # every bootstrapped worktree: branch, ports, URL
./wt dev <spec>      # run its dev server (its own ports)
./wt open <spec>     # open its frontend URL in the browser
./wt path <spec>     # print its path
```

`./wt` wraps `scripts/bootstrap_worktree.py` and `scripts/wt.py`. See
`docs/agents/commands.md` for the full command reference.
