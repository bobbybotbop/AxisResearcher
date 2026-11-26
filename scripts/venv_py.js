#!/usr/bin/env node
// Cross-platform helper: run a script with the venv Python.
// Usage: node scripts/venv_py.js app.py [args...]
const { spawnSync } = require('child_process');
const path = require('path');
const root = path.join(__dirname, '..');
const python = process.platform === 'win32'
  ? path.join(root, '.venv', 'Scripts', 'python.exe')
  : path.join(root, '.venv', 'bin', 'python3');
const result = spawnSync(python, process.argv.slice(2), { stdio: 'inherit', cwd: root });
process.exit(result.status ?? 1);
