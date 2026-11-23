"""
Pre-step for `npm run dev`: make sure this checkout has dev ports.

- Main checkout: nothing to do, it keeps the default 4000/5000.
- A git worktree that was never bootstrapped: bootstrap it automatically
  (copies .env, allocates a unique port pair, junctions .venv, installs
  frontend deps if node_modules is missing), so `npm run dev` just works
  in any worktree with zero manual steps.

Idempotent: already-bootstrapped worktrees reuse their registered ports.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bootstrap_worktree import find_main_checkout, bootstrap


def main() -> None:
    cwd = os.getcwd()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        return  # not a git repo; leave defaults alone
    root = os.path.normpath(result.stdout.strip())

    if root == os.path.normpath(find_main_checkout(root)):
        print("Main checkout: using default ports (frontend 4000, backend 5000).")
        return

    name = os.path.basename(root)
    has_deps = os.path.isdir(os.path.join(root, "frontend", "node_modules"))
    print(f"Worktree '{name}': ensuring its own dev ports ...")
    bootstrap(root, name, skip_install=has_deps, with_db=False)


if __name__ == "__main__":
    main()
