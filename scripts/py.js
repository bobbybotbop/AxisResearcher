#!/usr/bin/env node
// Cross-platform helper: run a Python script with the system Python.
// Usage: node scripts/py.js scripts/some_script.py [args...]
const { spawnSync } = require('child_process');
const python = process.platform === 'win32' ? 'python' : 'python3';
const result = spawnSync(python, process.argv.slice(2), { stdio: 'inherit' });
process.exit(result.status ?? 1);
