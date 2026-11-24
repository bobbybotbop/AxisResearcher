# Worktrees

`/implement-spec` runs in the main checkout: the integration branch lives there, and
merger subagents merge ticket branches into it. Only **implementer subagents** get
worktrees — one per ticket at `.worktrees/<spec>-<ticket>`, created with plain
`git worktree add` and removed when the ticket merges.

## Ticket worktrees are tests-only

Never run a dev server in a ticket worktree — the main checkout owns the single dev
stack (ports 4000/5000). There is no per-worktree port allocation, bootstrap step,
or `.env` copying.

## Running tests in a ticket worktree

Use the main checkout's venv with the worktree as the working directory — the venv
is just an interpreter plus site-packages, and cwd determines the code under test:

```
cd .worktrees/<spec>-<ticket>
../../.venv/Scripts/python -m pytest tests/ -x -q
```

No venv junction is needed.
