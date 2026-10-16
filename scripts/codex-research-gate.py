#!/usr/bin/env python3
# Copyright (c) 2026 Raymond Manaloto
"""Thin Codex research-hook adapter with script-derived repository authority."""

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

if __name__ == "__main__":
    raise SystemExit(
        import_module("dotfiles_setup.codex_research_gate").main(repo_root=REPO_ROOT)
    )
