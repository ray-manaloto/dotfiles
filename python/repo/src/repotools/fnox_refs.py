"""The fnox reference rule: a tracked fnox TOML's Doppler entries hold Doppler secret names, never values.

`fnox set NAME --provider <doppler>` does not reach Doppler. fnox 1.47.0's Doppler provider keeps the read-only
default capabilities (crates/fnox-core/src/providers/mod.rs:261-263), so `fnox set` stores the value itself as the
entry's `value` (src/commands/set.rs:563-565), and with no provider as its `default` too (set.rs:566-569). A real
Doppler entry's `value` is the secret's name, which fnox hands to `doppler secrets get <value> --plain`
(crates/fnox-core/src/providers/doppler.rs:114). Here that name is the entry's own key, so a `value` must equal it:
an upper-case leak such as a base32 seed would pass a name pattern, but not this. This reads the git index, the
snapshot a commit certifies, as zero_bash does, and names each bad entry by file and key, never by its value.
"""

import re
import sys
import tomllib
from collections.abc import Iterator, Mapping

from . import zero_bash
from .models import FnoxFinding, FnoxRule

# The names fnox reads (crates/fnox-core/src/config.rs:59-73): fnox.toml, fnox.<profile>.toml and fnox.local.toml,
# each also hidden and under .config/, plus the global config folder's files. Every other tracked TOML is checked
# too, since `import` can name any file (config.rs:1299-1311); only these must parse.
FNOX_NAME = re.compile(r"(?:.*/)?\.?fnox(?:\.[^/]+)?\.toml|(?:.*/)?\.config/fnox/[^/]+\.toml")
# An entry whose Doppler secret has another name than its key: {(path, dotted key): Doppler name}. None today.
RENAMES: Mapping[tuple[str, str], str] = {}

# A parsed TOML table; tomllib returns plain dicts, so there is no schema model to generate for it.
type Table = Mapping[str, object]


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
    entries = [(blob, path) for mode, blob, path in zero_bash.index() if mode in zero_bash.FILE_MODES]
    wanted = [(blob, path) for blob, path in entries if path.endswith(".toml")]
    content = zero_bash.blobs([blob for blob, _path in wanted])
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
