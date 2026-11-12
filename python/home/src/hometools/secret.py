"""secret-set: store one new Doppler secret in dotfiles/dev_personal from stdin, under the owner's write token.

`fnox set NAME --provider doppler_...` never reaches Doppler: fnox 1.47.0's Doppler provider keeps the read-only
default capabilities (crates/fnox-core/src/providers/mod.rs:261-263), so `fnox set` writes the value itself into
the TOML (src/commands/set.rs:563-565). This command sends it to Doppler instead.

The value goes from this process's stdin to doppler's stdin through a pipe: it is never an argument, never
printed or logged and never written to a file. The write token is the global fnox config's DOPPLER_WRITE_TOKEN, a
Keychain entry with env = false: `fnox get` reads it and this command hands it to doppler as DOPPLER_TOKEN, the one
variable doppler reads its token from (doppler 3.77.1 pkg/models/config.go:156). Inherited DOPPLER_* variables (an
API host, a TLS switch, another token) are dropped from the child's environment, so doppler gets only that token.

doppler reads piped stdin with a default bufio.Scanner (cmd/secrets.go:289-306): a line over 64 KiB fails the set,
and a line's trailing CR is dropped, so a CRLF value is stored with LF line ends.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NoReturn

from .models import Failure
from .proc import out

PROJECT, CONFIG, TOKEN = "dotfiles", "dev_personal", "DOPPLER_WRITE_TOKEN"
NAME = re.compile(r"[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*")


def stop(error: str) -> NoReturn:
    """The one JSON error event the command ends with; it never carries the value."""
    sys.stderr.write(Failure(error=f"secret:set: {error}").model_dump_json() + "\n")
    raise SystemExit(1)


def environment() -> dict[str, str]:
    """This process's environment without DOPPLER_*, plus the write token from `fnox get` as DOPPLER_TOKEN."""
    fnox = ["fnox", "--config", str(Path.home() / ".config/fnox/config.toml"), "--no-daemon", "--non-interactive"]
    argv = [*fnox, "get", TOKEN]
    try:
        found = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True, check=False)
    except OSError as failed:
        stop(f"fnox: {failed.strerror}")
    token = found.stdout.strip()
    if found.returncode or not token:
        stop(f"fnox could not read {TOKEN} from the Keychain (exit {found.returncode})")
    kept = {key: value for key, value in os.environ.items() if not key.startswith("DOPPLER_")}
    return {**kept, "DOPPLER_TOKEN": token}


def doppler(*argv: str) -> list[str]:
    """`doppler argv` for dotfiles/dev_personal."""
    return ["doppler", *argv, "--project", PROJECT, "--config", CONFIG]


def names(env: dict[str, str]) -> set[str]:
    """The secret names in dotfiles/dev_personal; `--only-names` asks Doppler for no values (cmd/secrets.go:179-185)."""
    argv = doppler("secrets", "--only-names", "--json")
    try:
        done = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True, env=env, check=False)
    except OSError as failed:
        stop(f"doppler: {failed.strerror}")
    if done.returncode:
        stop(f"listing the names in {PROJECT}/{CONFIG} failed (exit {done.returncode})")
    try:
        listed = json.loads(done.stdout)
    except json.JSONDecodeError:
        listed = None
    if not isinstance(listed, dict):
        stop(f"doppler listed the names in {PROJECT}/{CONFIG} as something other than a JSON object")
    return set(listed)


def read_value() -> bytes:
    """The value piped in on file descriptor 0, whole; a terminal is refused, because typing it would show it."""
    if os.isatty(0):
        stop("pipe the value in, for example: pbpaste | mise run secret:set NAME")
    with open(0, "rb", closefd=False) as stdin:
        value = stdin.read()
    if not value.strip():
        stop("the value is empty")
    return value


def set_secret(name: str) -> None:
    """Store NAME, refusing a name that is not UPPER_SNAKE, an empty value, and a name Doppler already has."""
    if not NAME.fullmatch(name):
        # Not echoed: a value pasted where the name goes would reach the log.
        stop("the name is not UPPER_SNAKE")
    value = read_value()
    env = environment()
    # A new name only: replacing a secret other programs read stays the owner's job in the Doppler dashboard.
    if name in names(env):
        stop(f"{name} already exists in {PROJECT}/{CONFIG}; change it in the Doppler dashboard")
    # Piped stdin is read line by line and joined by newlines, so a multi-line PEM keeps its lines and loses only
    # its final newline (cmd/secrets.go:263-306, utils/io.go:83-91). --silent: doppler prints the stored secret,
    # value included, after a set (cmd/secrets.go:392-394). --no-interactive: never prompt for it.
    argv = doppler("secrets", "set", name, "--silent", "--no-interactive")
    try:
        done = subprocess.run(argv, input=value, stdout=subprocess.DEVNULL, env=env, check=False)
    except OSError as failed:
        stop(f"doppler: {failed.strerror}")
    if done.returncode:
        stop(f"doppler secrets set {name} failed (exit {done.returncode})")
    out(f"secret:set: stored {name} in {PROJECT}/{CONFIG}")
