"""The fnox reference rule: a tracked fnox TOML's Doppler entries hold Doppler secret names, never values.

`fnox set NAME --provider <doppler>` does not reach Doppler. fnox 1.47.0's Doppler provider keeps the read-only
default capabilities (crates/fnox-core/src/providers/mod.rs:261-263), so `fnox set` stores the value itself as the
entry's `value` (src/commands/set.rs:563-565), and with no provider as its `default` too (set.rs:566-569). A real
Doppler entry's `value` is the secret's name, which fnox hands to `doppler secrets get <value> --plain`
(crates/fnox-core/src/providers/doppler.rs:114). Here that name is the entry's own key, so a `value` must equal it:
an upper-case leak such as a base32 seed would pass a name pattern, but not this. This reads the git index, the
snapshot a commit certifies, and names each bad entry by file and key, never by its value.
"""

import re
import subprocess
import sys
import tomllib
from collections.abc import Iterator, Mapping
from typing import cast

from . import process
from .models import FnoxFinding, FnoxRule

# The names fnox reads (crates/fnox-core/src/config.rs:59-73): fnox.toml, fnox.<profile>.toml and fnox.local.toml,
# each also hidden and under .config/, plus the global config folder's files. Every other tracked TOML is checked
# too, since `import` can name any file (config.rs:1299-1311); only these must parse.
FNOX_NAME = re.compile(r"(?:.*/)?\.?fnox(?:\.[^/]+)?\.toml|(?:.*/)?\.config/fnox/[^/]+\.toml")
# An entry whose Doppler secret has another name than its key: {(path, dotted key): Doppler name}. free-models
# reads Kilo's key as OPENAI_COMPATIBLE_API_KEY too.
RENAMES: Mapping[tuple[str, str], str] = {
    ("unix/home/.config/fnox/config.toml", "secrets.OPENAI_COMPATIBLE_API_KEY"): "KILO_API_KEY",
    # proxy run strips every name fnox defines, so the account ID is read under another name (the file says why).
    ("unix/home/.config/fnox/config.toml", "secrets.CF_ACCOUNT_ID"): "CLOUDFLARE_ACCOUNT_ID",
}

FILE_MODES = ("100644", "100755")  # Links (120000) and submodules (160000) have no content to read.

# A parsed TOML table; tomllib returns plain dicts, so there is no schema model to generate for it.
type Table = Mapping[str, object]


def git(*args: str, stdin: bytes | None = None) -> bytes:
    if stdin is None:
        return subprocess.run(["git", *args], capture_output=True, check=True).stdout
    # This call keeps the helper's default capture_stdout=True.
    return cast("bytes", process.run(["git", *args], stdin).stdout)


def index() -> list[tuple[str, str, str]]:
    """Mode, blob id and path of every index entry; :/ and --full-name list them all from any folder."""
    found = []
    for entry in git("ls-files", "-s", "-z", "--full-name", ":/").decode().split("\0")[:-1]:
        meta, path = entry.split("\t", 1)
        mode, blob, _stage = meta.split()
        found.append((mode, blob, path))
    return found


def blobs(ids: list[str]) -> dict[str, bytes]:
    """The content of each blob, read from the object store in one git call."""
    out = git("cat-file", "--batch", stdin="".join(f"{blob}\n" for blob in ids).encode())
    found: dict[str, bytes] = {}
    start = 0
    for _ in ids:
        header_end = out.index(b"\n", start)
        blob, _kind, size = out[start:header_end].decode().split()
        body = header_end + 1
        found[blob] = out[body : body + int(size)]
        start = body + int(size) + 1
    return found


def tables(node: object) -> Table:
    """node when it is a TOML table, else an empty one, so a malformed file yields no entries instead of failing."""
    return node if isinstance(node, dict) else {}


def scopes(config: Table) -> Iterator[tuple[str, Table]]:
    """The top level and each [profiles.<name>], with the dotted prefix of their keys."""
    yield "", config
    for name, profile in tables(config.get("profiles")).items():
        yield f"profiles.{name}.", tables(profile)


def doppler_providers(configs: Iterator[Table]) -> set[str]:
    """Every provider name of type doppler, in any file and scope: one file can use another's provider."""
    return {
        name
        for config in configs
        for _prefix, scope in scopes(config)
        for name, provider in tables(scope.get("providers")).items()
        if tables(provider).get("type") == "doppler"
    }


def check_config(path: str, config: Table, doppler: set[str]) -> Iterator[FnoxFinding]:
    for prefix, scope in scopes(config):
        # The file's own default_provider; one inherited from another file through fnox's merge is not seen here.
        fallback = scope.get("default_provider", config.get("default_provider"))
        for key, entry in tables(scope.get("secrets")).items():
            entry = tables(entry)  # noqa: PLW2901 - the same entry, as a table
            if entry.get("provider", fallback) not in doppler:
                continue
            where = f"{prefix}secrets.{key}"
            value = entry.get("value")
            if value is not None and value != RENAMES.get((path, where), key):
                yield FnoxFinding(path=path, key=where, rule=FnoxRule.value_not_a_reference)
            if "default" in entry:
                yield FnoxFinding(path=path, key=where, rule=FnoxRule.default_on_doppler)


def findings() -> list[FnoxFinding]:
    entries = [(blob, path) for mode, blob, path in index() if mode in FILE_MODES]
    wanted = [(blob, path) for blob, path in entries if path.endswith(".toml")]
    content = blobs([blob for blob, _path in wanted])
    configs: dict[str, Table] = {}
    for blob, path in wanted:
        try:
            configs[path] = tomllib.loads(content[blob].decode())
        except ValueError as error:  # tomllib's and UTF-8 decoding's errors: a fnox file's is named for main()
            if FNOX_NAME.fullmatch(path):
                msg = f"{path}: {error}"
                raise ValueError(msg) from error
    doppler = doppler_providers(iter(configs.values()))
    return [finding for path, config in configs.items() for finding in check_config(path, config, doppler)]


def report() -> None:
    """Print every finding as a JSON line and fail on any."""
    found = findings()
    sys.stdout.writelines(finding.model_dump_json() + "\n" for finding in found)
    if found:
        raise SystemExit(1)
