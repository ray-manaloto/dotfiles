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
# FindPython's own records hold a signature of the venv path; the resolved interpreter is hashed instead.
_PYTHON_RECORDS = "_Python3_"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_sha(top: Path) -> str:
    """Every file under top by relative path and content; a link counts by where it points."""
    digest = hashlib.sha256()
    for here, _, names in sorted(top.walk()):
        for path in (here / name for name in sorted(names)):
            digest.update(str(path.relative_to(top)).encode())
            digest.update(str(path.readlink()).encode() if path.is_symlink() else path.read_bytes())
    return digest.hexdigest()


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
    inputs = {
        "commit": commit,
        "patches": {file.name: sha(file) for file in sorted(patches.glob("*.patch"))},
        "uv_lock": sha(config.PROJECT / "uv.lock"),
        "cmake": cmake,
        "python": sha(Path(sys.executable).resolve()),
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
