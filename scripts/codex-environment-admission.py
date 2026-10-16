#!/usr/bin/env python3
# Copyright (c) 2026 Raymond Manaloto
"""PreToolUse admission adapter; activate only after trusted native qualification."""

from __future__ import annotations

import sys
from importlib import import_module
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "python" / "src"))

if __name__ == "__main__":
    admission = import_module("dotfiles_setup.environment_admission")
    raise SystemExit(admission.pretooluse_main())
