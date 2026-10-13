#!/usr/bin/env python3
# Copyright (c) 2026 Raymond Manaloto
"""Admit and execute required saved proof verifiers without inline substitutes."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "python" / "src"))

if __name__ == "__main__":
    raise SystemExit(import_module("dotfiles_setup.verification_admission").main())
