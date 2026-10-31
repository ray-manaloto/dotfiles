"""The build id: everything CMake found (DL-811), read from its file API after configure."""

import hashlib
import json
import sys
from pathlib import Path

from . import config
from .models import Config

_KINDS = ("cache-v2", "toolchains-v1", "cmakeFiles-v1")
# These change how the build runs, not what it produces.
_VOLATILE = (
    "CMAKE_C_COMPILER_LAUNCHER",
    "CMAKE_CXX_COMPILER_LAUNCHER",
    "LLVM_PARALLEL_COMPILE_JOBS",
    "LLVM_PARALLEL_LINK_JOBS",
    "LLVM_PARALLEL_TABLEGEN_JOBS",
)
# FindPython's own records hold a signature of the venv path; the resolved interpreter is hashed instead,
# with what lldb links and includes.
_PYTHON_RECORDS = "_Python3_"
_PYTHON_LINKED = ("_Python3_LIBRARY_RELEASE", "_Python3_INCLUDE_DIR")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha(top: Path) -> str:
    """Every file under top by relative path and content, through links; a broken link counts by where it points."""
    digest = hashlib.sha256()

    def add(folder: Path, above: tuple[Path, ...]) -> None:
        real = folder.resolve()
        if real in above:  # A link back up counts by how far up it points, which a moved folder keeps.
            digest.update(f"{folder.relative_to(top)} up {len(above) - above.index(real)}".encode())
            return
        for path in sorted(folder.iterdir()):
            if path.is_dir():
                add(path, (*above, real))
                continue
            digest.update(str(path.relative_to(top)).encode())
            digest.update(path.read_bytes() if path.exists() else str(path.readlink()).encode())

    add(top, ())
    return digest.hexdigest()


def forget_sub_builds(built: Path) -> None:
    """Remove every sub-build's cache: --fresh resets only the top one, and a sub-build keeps old settings."""
    for cache in built.rglob("CMakeCache.txt"):
        if cache.parent != built:
            cache.unlink()
    # Without its configure stamp a sub-build writes the cache again from its arguments.
    for stamp in built.rglob("*-stamp*/*-configure"):
        stamp.unlink()


def query(built: Path) -> None:
    """Ask CMake to write its file API replies on the next configure."""
    folder = built / ".cmake/api/v1/query"
    folder.mkdir(parents=True, exist_ok=True)
    for kind in _KINDS:
        (folder / kind).touch()


def replies(built: Path) -> tuple[str, dict[str, dict]]:
    """The CMake version, and each reply by kind, from the newest index."""
    folder = built / ".cmake/api/v1/reply"
    index = json.loads(max(folder.glob("index-*.json")).read_text())
    found = {item["kind"]: json.loads((folder / item["jsonFile"]).read_text()) for item in index["objects"]}
    return index["cmake"]["version"]["string"], found


def write(cfg: Config, commit: str, patches: Path, bootstrap: Path, sdk: Path) -> str:
    """Write what the build found to the inputs file; the id is the commit and that file's digest."""
    cmake, found = replies(config.build_tree(cfg))
    # A file counts by its content, so a replaced tool changes the id and a moved one does not. Values
    # inside these folders differ by worktree and say nothing about the build.
    inside = (str(cfg.cache), str(config.PROJECT))
    files: dict[str, str] = {}

    def by_content(path: Path) -> str:
        digest = sha(path)
        files[digest] = f".../{path.name}"
        return digest

    cache: dict[str, str] = {}
    for entry in found["cache"]["entries"]:
        name, value = entry["name"], entry["value"]
        if name in _VOLATILE or name.startswith(_PYTHON_RECORDS) or any(folder in value for folder in inside):
            continue
        path = Path(value)
        cache[name] = by_content(path) if path.is_absolute() and path.is_file() else value
    for item in found["cmakeFiles"]["inputs"]:
        path = Path(item["path"])
        # bootstrap.cmake counts through the values it set, so a comment in it changes nothing.
        if item.get("isExternal") and not item.get("isCMake") and path.is_file() and path != bootstrap:
            by_content(path)
    linked = {e["name"]: Path(e["value"]) for e in found["cache"]["entries"] if e["name"] in _PYTHON_LINKED}
    inputs = {
        "commit": commit,
        "patches": {file.name: sha(file) for file in sorted(patches.glob("*.patch"))},
        "uv_lock": sha(config.PROJECT / "uv.lock"),
        "cmake": cmake,
        "python": sha(Path(sys.executable).resolve()),
        "python_linked": {name: tree_sha(path) if path.is_dir() else sha(path) for name, path in linked.items()},
        # Compiles read SDK headers that configure never named, so the file API cannot cover them.
        "sdk": tree_sha(sdk),
        "compilers": {
            chain["language"]: f"{chain['compiler']['id']} {chain['compiler']['version']}"
            for chain in found["toolchains"]["toolchains"]
            if "id" in chain["compiler"]  # Languages the project never enabled are listed without one.
        },
        "cache": cache,
        "files": files,
    }
    target = config.inputs_file(cfg)
    target.write_text(json.dumps(inputs, indent=2, sort_keys=True) + "\n")
    return f"{commit}-{sha(target)[:12]}"
