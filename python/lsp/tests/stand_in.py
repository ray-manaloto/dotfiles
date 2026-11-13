#!/usr/bin/env -S python3 -I
"""mise in the tests: a networked call answers from a script, the rest run for real (python/home's stand_in.py)."""

# mise use @latest, mise outdated and the bootstrap upgrade dry run read the network (CODING_STANDARDS 2): a test
# links this file as `mise` in a folder ahead of the real one on PATH. $STAND_IN/script.json maps a call, its argv
# as a JSON list, to {"stdout", "stderr", "code"}; or to {"real": true}, the real mise with the stand-in off PATH;
# or to {"real": true, "argv": [...]}, the real mise with those arguments instead, the offline call that does the
# same job (mise use of the installed version for mise use @latest). A call it does not name fails with 127, as a
# missing command does, so nothing reaches the network by mistake. Every call's JSON argv is a line of
# $STAND_IN/calls.jsonl.

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

folder = Path(os.environ["STAND_IN"])
link = Path(sys.argv[0])
call = json.dumps([link.name, *sys.argv[1:]])
with (folder / "calls.jsonl").open("a") as log:
    log.write(call + "\n")
answer = json.loads((folder / "script.json").read_text()).get(call)
if answer is None:
    sys.stderr.write(f"stand-in: no answer for {call}\n")
    raise SystemExit(127)
if answer.get("real"):
    rest = os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep) if Path(p) != link.parent)
    program = shutil.which(link.name, path=rest)
    if program is None:
        sys.stderr.write(f"stand-in: no real {link.name} on PATH\n")
        raise SystemExit(127)
    argv = answer.get("argv", sys.argv[1:])
    raise SystemExit(subprocess.run([program, *argv], env=os.environ | {"PATH": rest}, check=False).returncode)
sys.stdout.write(answer.get("stdout", ""))
sys.stderr.write(answer.get("stderr", ""))
raise SystemExit(answer.get("code", 0))
