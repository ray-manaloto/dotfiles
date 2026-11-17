"""pending-updates: the PC's waiting package updates for each source, listed and never applied (ticket #733)."""

# The official repositories through checkupdates (pacman-contrib 1.13.1): it syncs a temporary database under
# /tmp/checkup-db-<uid> and never touches the live one or any package; it lists `<name> <old> -> <new>` and exits 0,
# exits 2 when nothing waits and 1 when it cannot sync (checkupdates.sh.in:150-181). It discards pacman -Qu's own
# errors (line 155), so a failed comparison after a good sync reads as exit 2: an upstream limit this check inherits.
# The AUR through yay -Qua (yay 13.0.1): the same shape, then an age badge when the AUR reports when the package
# last changed, such as ` [2d]`, ` [38d8h]`, ` [1h30m]` or ` [45m]` (print.go:173-179, FormatAgeTag and
# FormatDuration in pkg/text/time.go); a clock ahead of the AUR's gives negative parts such as ` [-5m]`. The badge is
# the age at this run, so it stays out of the items, which list the update alone. yay -Qua exits 0
# with the list, and exit 1 both when nothing waits (an empty error, which yay does not print) and when the AUR query
# failed (the error on stderr), so exit 1 with no output at all is the only "none" (yay print.go:122-200,
# pkg/upgrade/service.go:60-191, main.go). yay prints only after the whole query, so lines with any other exit are a
# listing cut short. Neither tool colours a pipe. A source it could not read is unknown and the other source's
# answer stands: an AUR outage never reads as up to date. omarchy update -y is the PC's one upgrade step.

import re
import subprocess
from collections.abc import Callable

from .models import PcDoctorLine, Result

CHECK = "pending-updates"
MISSING = 127  # the PC's shell: command not found
UPDATE = re.compile(r"(?P<update>\S+ \S+ -> \S+)")
AGED = re.compile(r"(?P<update>\S+ \S+ -> \S+)( \[(-?\d+[dhm]){1,2}\])?")
# Each source: its name, its command on the PC, the exit that lists, the exit that is "none" when nothing was
# printed, and the shape of one listed line (its update group is what the items keep).
SOURCES = (
    ("official", ("checkupdates",), 0, 2, UPDATE),
    ("aur", ("yay", "-Qua"), 0, 1, AGED),
)


def read(
    argv: tuple[str, ...], lists: int, none: int, shape: re.Pattern[str], done: subprocess.CompletedProcess[str] | str
) -> list[str] | str:
    """The listed updates, or why this source is unknown."""
    if isinstance(done, str):
        return done
    tool = " ".join(argv)
    lines = done.stdout.splitlines()
    if done.returncode == MISSING:
        return f"{argv[0]} was not found on the PC's PATH"
    if done.returncode == none and not lines:
        # yay's "none" and its failure share exit 1; only the failure prints.
        return f"{tool} exited {none} with an error" if done.stderr.strip() else []
    if done.returncode != lists:
        return f"{tool} exited {done.returncode}"
    matched = [shape.fullmatch(line) for line in lines]
    if not matched or None in matched:
        return f"{tool}'s output did not parse"
    return [found["update"] for found in matched if found]


def line(run: Callable[[tuple[str, ...]], subprocess.CompletedProcess[str] | str]) -> PcDoctorLine:
    """One line for both sources: pass with every waiting update, or unknown naming each source it could not read."""
    items, parts, culprits = [], [], []
    for source, argv, lists, none, shape in SOURCES:
        found = read(argv, lists, none, shape, run(argv))
        if isinstance(found, str):
            parts.append(f"{source}: unknown ({found})")
            culprits.append(source)
        else:
            parts.append(f"{source}: {len(found) or 'none'} waiting")
            items += [f"{source}:{update}" for update in found]
    result = Result.unknown if culprits else Result.pass_
    return PcDoctorLine(check=CHECK, result=result, detail="; ".join(parts), culprits=culprits, items=items)
