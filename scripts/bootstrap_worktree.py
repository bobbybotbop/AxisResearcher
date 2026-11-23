"""
Bootstrap a git worktree so it can run its own dev stack alongside the main
checkout and other worktrees.

Does the following:
  1. Copies the main checkout's .env into the worktree (if missing).
  2. Allocates a unique frontend/backend port pair, recorded in
     .scratch/worktree-ports.json in the MAIN checkout, and writes
     AXIS_FRONTEND_PORT / AXIS_BACKEND_PORT into the worktree's .env.
  3. Junctions the main checkout's .venv into the worktree (Windows mklink /J;
     safe to share, it's read-only at runtime).
  4. Syncs backend dependencies: pip install -r requirements.txt into the
     (shared) venv, so a venv that drifted from the spec can't crash app.py.
  5. Runs `npm install` in the worktree's frontend/ (skip with --skip-install).
  6. Optionally copies axis.db* so the worktree starts with real data (--with-db).

Usage:
    python scripts/bootstrap_worktree.py <worktree-path> [--name NAME]
        [--skip-install] [--with-db]
"""

import argparse
import json
import os
import shutil
import socket
import subprocess
import sys

REGISTRY_REL = os.path.join(".scratch", "worktree-ports.json")


def _git(args: list[str], cwd: str) -> str:
    result = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def find_main_checkout(cwd: str) -> str:
    """First entry of `git worktree list --porcelain` is always the main worktree."""
    out = _git(["worktree", "list", "--porcelain"], cwd)
    for line in out.splitlines():
        if line.startswith("worktree "):
            return os.path.normpath(line[len("worktree "):])
    raise RuntimeError("could not determine main checkout")


def _load_registry(main: str) -> dict:
    path = os.path.join(main, REGISTRY_REL)
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"worktrees": {}}


def _save_registry(main: str, registry: dict) -> None:
    path = os.path.join(main, REGISTRY_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
    os.replace(tmp, path)


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0


def allocate_ports(registry: dict) -> tuple[int, int]:
    """Next free (frontend, backend) pair, stepping by 10 from 4100/5100."""
    used = set()
    for entry in registry.get("worktrees", {}).values():
        used.add(entry["frontend"])
        used.add(entry["backend"])
    n = 1
    while True:
        frontend, backend = 4000 + n * 10, 5000 + n * 10
        if frontend not in used and backend not in used and _port_free(frontend) and _port_free(backend):
            return frontend, backend
        n += 1


def _set_env_values(env_path: str, updates: dict[str, str]) -> None:
    lines: list[str] = []
    if os.path.exists(env_path):
        with open(env_path, encoding="utf-8") as f:
            lines = f.read().splitlines()
    remaining = dict(updates)
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.partition("=")[0].strip()
            if key in remaining:
                lines[i] = f"{key}={remaining.pop(key)}"
    for key, value in remaining.items():
        lines.append(f"{key}={value}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _junction_venv(main: str, worktree: str) -> None:
    src = os.path.join(main, ".venv")
    dst = os.path.join(worktree, ".venv")
    if os.path.exists(dst) or not os.path.isdir(src):
        return
    if sys.platform == "win32":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", dst, src], capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"WARNING: could not junction .venv: {result.stderr.strip()}")
            print(f"         run: cmd /c mklink /J \"{dst}\" \"{src}\"")
    else:
        os.symlink(src, dst)


def _sync_requirements(worktree: str) -> None:
    reqs = os.path.join(worktree, "requirements.txt")
    venv_python = os.path.join(
        worktree, ".venv", "Scripts" if sys.platform == "win32" else "bin", "python"
    )
    if not os.path.isfile(reqs) or not os.path.exists(venv_python):
        return
    print("Syncing backend dependencies (pip install -r requirements.txt) ...")
    subprocess.run(
        [venv_python, "-m", "pip", "install", "-q", "-r", "requirements.txt"],
        cwd=worktree,
        check=True,
    )


def bootstrap(worktree: str, name: str, skip_install: bool, with_db: bool) -> None:
    worktree = os.path.normpath(os.path.abspath(worktree))
    if not os.path.isfile(os.path.join(worktree, ".git")) and not os.path.isdir(os.path.join(worktree, ".git")):
        raise RuntimeError(f"{worktree} does not look like a git worktree (no .git)")
    main = find_main_checkout(worktree)
    branch = _git(["branch", "--show-current"], worktree).strip()

    registry = _load_registry(main)
    entry = registry["worktrees"].get(name)
    if entry:
        frontend, backend = entry["frontend"], entry["backend"]
        print(f"Ports already registered for '{name}': frontend={frontend} backend={backend}")
    else:
        frontend, backend = allocate_ports(registry)

    # .env: copy from main if missing, then pin this worktree's ports
    main_env = os.path.join(main, ".env")
    wt_env = os.path.join(worktree, ".env")
    if not os.path.exists(wt_env) and os.path.exists(main_env):
        shutil.copy2(main_env, wt_env)
        print("Copied .env from main checkout.")
    _set_env_values(wt_env, {
        "AXIS_FRONTEND_PORT": str(frontend),
        "AXIS_BACKEND_PORT": str(backend),
    })
    print(f".env pinned: AXIS_FRONTEND_PORT={frontend} AXIS_BACKEND_PORT={backend}")

    _junction_venv(main, worktree)
    print(f".venv linked from {main}")

    _sync_requirements(worktree)

    if with_db:
        for suffix in ("", "-wal", "-shm"):
            src = os.path.join(main, f"axis.db{suffix}")
            if os.path.exists(src):
                shutil.copy2(src, os.path.join(worktree, f"axis.db{suffix}"))
        print("Copied axis.db from main checkout.")

    if not skip_install:
        frontend_dir = os.path.join(worktree, "frontend")
        if os.path.isdir(frontend_dir):
            print("Installing frontend dependencies (npm install) ...")
            subprocess.run("npm install", cwd=frontend_dir, shell=True, check=True)
        else:
            print("No frontend/ directory in worktree; skipping install.")

    registry["worktrees"][name] = {
        "path": worktree,
        "branch": branch,
        "frontend": frontend,
        "backend": backend,
    }
    _save_registry(main, registry)

    print()
    print(f"Worktree '{name}' ready:")
    print(f"  path     {worktree}")
    print(f"  branch   {branch}")
    print(f"  frontend http://localhost:{frontend}")
    print(f"  backend  http://localhost:{backend}")
    print(f"  dev      cd \"{worktree}\" && npm run dev")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap a worktree with its own dev ports.")
    parser.add_argument("worktree", help="Path to the worktree (e.g. .worktrees/my-spec)")
    parser.add_argument("--name", help="Registry name (default: worktree directory name)")
    parser.add_argument("--skip-install", action="store_true", help="Skip frontend npm install")
    parser.add_argument("--with-db", action="store_true", help="Copy axis.db from the main checkout")
    args = parser.parse_args()

    worktree = os.path.normpath(os.path.abspath(args.worktree))
    name = args.name or os.path.basename(worktree)
    bootstrap(worktree, name, args.skip_install, args.with_db)


if __name__ == "__main__":
    main()
