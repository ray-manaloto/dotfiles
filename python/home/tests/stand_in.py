#!/usr/bin/env -S python3 -I
"""The update tasks' programs in their tests: a networked call answers from a script, the rest run for real."""

# brew update, brew upgrade, brew outdated, mise outdated and mise upgrade download or read the network, as do the
# programs update:all's other leaves run (CODING_STANDARDS 2): a test links this file as `brew` and `mise` in a
# folder ahead of the real ones on PATH, and as each leaf program where its task body names it. The link's name is
# the call's first word. $STAND_IN/script.json maps a call, its argv as a JSON list, to {"stdout", "stderr",
# "code", "signal"}, where "signal" is one it then kills itself with; or to {"real": true}, the next program of
# its name on PATH with the stand-ins off it, as brew list --pinned and mise run toolchain:verify run on the
# scratch toolchain; or to {"real": "<path>"}, that program. A call it does not name fails with 127, as a
# missing command does, so nothing reaches the network by mistake.
# Every call's JSON argv is a line of $STAND_IN/calls.jsonl.

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
real = answer.get("real")
if real:
    # Without the stand-ins on PATH: what the real call runs, toolchain:verify's own brew and mise, is real too.
    rest = os.pathsep.join(p for p in os.environ["PATH"].split(os.pathsep) if Path(p) != link.parent)
    program = real if isinstance(real, str) else shutil.which(link.name, path=rest)
    if program is None:
        sys.stderr.write(f"stand-in: no real {link.name} on PATH\n")
        raise SystemExit(127)
    env = os.environ | {"PATH": rest}
    raise SystemExit(subprocess.run([program, *sys.argv[1:]], env=env, check=False).returncode)
sys.stdout.write(answer.get("stdout", ""))
sys.stderr.write(answer.get("stderr", ""))
if "signal" in answer:
    sys.stdout.flush()
    sys.stderr.flush()
    os.kill(os.getpid(), answer["signal"])
raise SystemExit(answer.get("code", 0))
