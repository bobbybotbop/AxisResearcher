"""
Switch between bootstrapped worktrees (see scripts/bootstrap_worktree.py).

Usage:
    python scripts/wt.py list            # name, branch, ports, URL for every worktree
    python scripts/wt.py path <name>     # print the worktree path (for: cd "$(python scripts/wt.py path x)")
    python scripts/wt.py dev <name>      # run `npm run dev` in that worktree (its own ports)
    python scripts/wt.py open <name>     # open the worktree's frontend URL in the browser
"""

import argparse
import os
import subprocess
import sys
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bootstrap_worktree import find_main_checkout, _load_registry


def _registry() -> dict:
    main = find_main_checkout(os.getcwd())
    return _load_registry(main)


def _get(registry: dict, name: str) -> dict:
    entry = registry.get("worktrees", {}).get(name)
    if not entry:
        known = ", ".join(registry.get("worktrees", {})) or "(none)"
        raise SystemExit(f"unknown worktree '{name}'. Registered: {known}")
    return entry


def cmd_list() -> None:
    registry = _registry()
    entries = registry.get("worktrees", {})
    if not entries:
        print("No bootstrapped worktrees. Run scripts/bootstrap_worktree.py first.")
        return
    for name, e in entries.items():
        status = "ok" if os.path.isdir(e["path"]) else "MISSING"
        print(f"{name}  [{status}]")
        print(f"  branch   {e.get('branch', '?')}")
        print(f"  path     {e['path']}")
        print(f"  frontend http://localhost:{e['frontend']}   backend http://localhost:{e['backend']}")


def cmd_path(name: str) -> None:
    print(_get(_registry(), name)["path"])


def cmd_dev(name: str) -> None:
    entry = _get(_registry(), name)
    print(f"Starting dev for '{name}' on ports {entry['frontend']}/{entry['backend']} ...")
    subprocess.run("npm run dev", cwd=entry["path"], shell=True)


def cmd_open(name: str) -> None:
    entry = _get(_registry(), name)
    webbrowser.open(f"http://localhost:{entry['frontend']}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Switch between bootstrapped worktrees.")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    p = sub.add_parser("path"); p.add_argument("name")
    p = sub.add_parser("dev"); p.add_argument("name")
    p = sub.add_parser("open"); p.add_argument("name")
    args = parser.parse_args()

    if args.command == "list":
        cmd_list()
    elif args.command == "path":
        cmd_path(args.name)
    elif args.command == "dev":
        cmd_dev(args.name)
    elif args.command == "open":
        cmd_open(args.name)


if __name__ == "__main__":
    main()
