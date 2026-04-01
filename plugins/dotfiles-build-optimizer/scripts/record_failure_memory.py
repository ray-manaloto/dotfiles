#!/usr/bin/env python3
"""Append a failure-memory entry for the repo-local build optimizer plugin."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to a JSON report")
    parser.add_argument(
        "--memory-path",
        default=".omx/state/dotfiles-build-optimizer/failure-memory.jsonl",
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    payload["recorded_at"] = datetime.now(UTC).isoformat()
    memory_path = Path(args.memory_path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with memory_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
