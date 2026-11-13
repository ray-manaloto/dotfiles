"""rea-install: the one pinned rea package (data/rea-pin.json), installed project-style in jbctl's rea folder."""

# The package is a build of one rea commit, published as a dotfiles release asset; its sha256 is checked against the
# pin before any use. npm installs it from that file with overrides generated from the package's own
# npm-shrinkwrap.json, in an environment that reads no user or global npm config, into a candidate folder that then
# takes the place of the old one.

import contextlib
import datetime as dt
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
from collections.abc import Generator, Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

import httpx

from .models import NpmLock, NpmLockPackage, ReaFolder, ReaIdentity, ReaPin

ARCHIVE = "package.tgz"
PACKAGE = "node_modules/rea-agents"
HELPER = f"{PACKAGE}/bridge/native/ReaNativeUI.swift"
REA = "node_modules/.bin/rea"
IDENTITY = "identity.json"
SHRINKWRAP = "package/npm-shrinkwrap.json"
NPM_INSTALL = ["npm", "install", "--ignore-scripts", "--no-audit", "--no-fund"]
# Where the old folder waits during a swap, beside the rea folder, until the new one is patched and recorded.
PREVIOUS = ".rea-previous"
# The rea-install task's mise.toml. Only a source checkout has it: rea-install runs as that task, never as an installed
# jbctl, so no other command reads it.
TASKS = Path(__file__).resolve().parents[2] / "mise.toml"


def pin() -> ReaPin:
    return ReaPin.model_validate_json(files("jbctl").joinpath("data/rea-pin.json").read_text())


def folder() -> Path:
    """<XDG_DATA_HOME>/jbctl/rea; an unset, empty or relative XDG_DATA_HOME means ~/.local/share (XDG spec)."""
    data = Path(os.environ.get("XDG_DATA_HOME", ""))
    return (data if data.is_absolute() else Path.home() / ".local/share") / "jbctl/rea"


def sha256(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def patch_sha256() -> str:
    """The sha256 of the rea-native-ui.patch that ships in this package."""
    return hashlib.sha256(files("jbctl").joinpath("rea-native-ui.patch").read_bytes()).hexdigest()


def record(root: Path, want: ReaPin, node: str, *, keep: bool) -> ReaIdentity:
    """Write root/identity.json for the verified, patched install; keep an earlier file when the install was kept."""
    written = root / IDENTITY
    if keep and written.is_file():
        return ReaIdentity.model_validate_json(written.read_text())
    identity = ReaIdentity(
        source_sha=want.source_sha,
        package_sha256=sha256(root / ARCHIVE),
        patch_sha256=patch_sha256(),
        node_version=node,
        installed_at=dt.datetime.now(dt.UTC),
    )
    written.write_text(identity.model_dump_json(indent=2) + "\n")
    return identity


def checked(archive: Path, want: ReaPin) -> Path:
    """The archive, if its sha256 is the pin's; anything else is refused before it is opened."""
    have = sha256(archive)
    if have != want.package_sha256:
        msg = f"{archive}: sha256 {have} is not the pin's {want.package_sha256}"
        raise ValueError(msg)
    return archive


def fetch(url: str, dest: Path) -> Path:
    """Download url to dest, following the release's redirect to its storage."""
    with httpx.stream("GET", url, follow_redirects=True, timeout=60) as response, dest.open("xb") as file:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            file.write(chunk)
    return dest


Packages = Mapping[str, NpmLockPackage]


def resolve(packages: Packages, key: str, dep: str) -> str | None:
    """Node's lookup: node_modules/<dep> in key's folder, then in each enclosing package's, up to the root."""
    while True:
        candidate = f"{key}/node_modules/{dep}" if key else f"node_modules/{dep}"
        if candidate in packages:
            return candidate
        if not key:
            return None
        key = key.rsplit("/node_modules/", 1)[0] if "/node_modules/" in key else ""


def subtree(packages: Packages, key: str, path: frozenset[str]) -> dict[str, Any]:
    """key's version and, under each dependency's name, its own subtree; a cycle stops at a package on the path."""
    meta = packages[key]
    out: dict[str, Any] = {".": meta.version}
    for dep in sorted({**(meta.dependencies or {}), **(meta.optional_dependencies or {})}):
        hit = resolve(packages, key, dep)
        if hit is not None and hit not in path:
            out[dep] = subtree(packages, hit, path | {hit})
    return out


def overrides(lock: NpmLock) -> dict[str, Any]:
    """npm overrides that pin rea's optional dependencies' whole subtree to the lock, nested along each path.

    rea keeps optional Frida out of its bundle, so npm resolves Frida's subtree fresh and the shrinkwrap does not
    apply to it. A flat, parent-keyed form does not work: arborist takes a key from the nearest override set first
    (@npmcli/arborist lib/override-set.js lines 168-181), so a rule for "rea-agents > frida" hides a top-level
    "frida" rule's children. A dependency with no lock entry is another platform's optional and is left out.
    """
    packages = {key: meta for key, meta in lock.packages.items() if not meta.dev}
    pins = {}
    for dep in sorted(packages[""].optional_dependencies or {}):
        hit = resolve(packages, "", dep)
        if hit is not None:
            pins[dep] = subtree(packages, hit, frozenset({hit}))
    return {"rea-agents": pins}


def npm_env(tmp: Path) -> dict[str, str]:
    """PATH, an empty HOME (so a fresh cache, ~/.npm) and TMPDIR, and empty user and global npm config files.

    PATH starts with the folder of the node on PATH, which holds the npm that Node bundles, so a separately
    installed npm (the global config's npm tool) cannot shadow it. Nothing else is inherited, so no npm_config_* or
    NPM_CONFIG_* variable reaches npm. npm refuses one file for both configs, so there are two.
    """
    for name in ("user", "global"):
        (tmp / name).touch()
    (tmp / "home").mkdir()
    path = os.environ.get("PATH", "")
    node = shutil.which("node", path=path)
    return {
        "PATH": os.pathsep.join([str(Path(node).parent), path]) if node else path,
        "HOME": str(tmp / "home"),
        "TMPDIR": str(tmp),
        "npm_config_userconfig": str(tmp / "user"),
        "npm_config_globalconfig": str(tmp / "global"),
    }


def task_tools() -> dict[str, str]:
    """The Node and npm the rea-install task names (mise.toml, the one place they are written): its Node tool,
    and in JBCTL_REA_NPM the version of the npm that Node bundles."""
    if not TASKS.is_file():
        msg = f"no {TASKS}: run rea-install as `mise run //jbctl:rea-install` from a dotfiles checkout"
        raise ValueError(msg)
    task = tomllib.loads(TASKS.read_text())["tasks"]["rea-install"]
    return {"node": task["tools"]["node"], "npm": task["env"]["JBCTL_REA_NPM"]}


def check_tools(tools: Mapping[str, str], env: Mapping[str, str]) -> None:
    """Each tool on env's PATH reports its pinned version. mise puts a task tool it did not install nowhere, and
    the command then finds whatever else is on PATH, so a missing one is refused here rather than used."""
    for name, want in tools.items():
        done = subprocess.run([name, "--version"], env=env, capture_output=True, text=True, check=True)
        have = done.stdout.strip().removeprefix("v")
        if have != want:
            msg = f"{name} {have} on PATH is not the task's {want}"
            raise ValueError(msg)


def intact(root: Path, want: ReaPin) -> bool:
    """root's rea-agents is the pinned version and has its helper and rea; one with any of them missing, or a
    package.json that does not read, is installed again."""
    meta = root / PACKAGE / "package.json"
    if not ((root / HELPER).is_file() and (root / REA).is_file()):
        return False
    with contextlib.suppress(OSError, ValueError, KeyError, TypeError):
        return json.loads(meta.read_text())["version"] == want.package_version
    return False


def verified(root: Path, want: ReaPin, *, reused: bool) -> ReaFolder:
    """rea-agents at the pinned version, with its native UI helper; refused otherwise."""
    version = json.loads((root / PACKAGE / "package.json").read_text())["version"]
    helper = root / HELPER
    if version != want.package_version or not helper.is_file():
        msg = f"{root}: rea-agents {version} {'with' if helper.is_file() else 'without'} {HELPER}, not the pin's"
        raise ValueError(msg)
    return ReaFolder(folder=str(root), version=version, helper=str(helper), reused=reused)


def project(archive: str, lock: NpmLock) -> dict[str, Any]:
    """The package.json of a rea folder: the archive as its one dependency, with the lock's overrides."""
    return {"private": True, "dependencies": {"rea-agents": f"file:{archive}"}, "overrides": overrides(lock)}


def replaceable(target: Path) -> None:
    """Refuse a target that holds anything but a rea folder this command made, and a previous swap's leftover."""
    previous = target.with_name(PREVIOUS)
    if previous.exists():
        msg = f"{previous} holds a rea folder from a swap that did not finish: move it back to {target} or remove it"
        raise ValueError(msg)
    if not target.exists():
        return
    made = target / "package.json"
    with contextlib.suppress(OSError, ValueError):  # missing, unreadable or not JSON: not a folder this command made
        if json.loads(made.read_text()).get("dependencies") == {"rea-agents": f"file:{ARCHIVE}"}:
            return
    msg = f"{target} is not a rea folder that rea-install made; move it away first"
    raise ValueError(msg)


def install(archive: Path, target: Path, want: ReaPin, tools: Mapping[str, str]) -> ReaFolder:
    """npm-install the checked archive into a candidate folder beside target, verify it, then swap it in. The old
    folder waits beside target (PREVIOUS) for settled() to remove it or put it back."""
    replaceable(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=".rea-") as work:
        candidate = Path(work) / "rea"
        candidate.mkdir()
        # A copy inside the folder: file: resolves against package.json, so the folder moves as one.
        shutil.copyfile(checked(archive, want), candidate / ARCHIVE)
        with tarfile.open(candidate / ARCHIVE) as tgz:
            member = tgz.extractfile(SHRINKWRAP) if SHRINKWRAP in tgz.getnames() else None
            if member is None:
                msg = f"{archive}: no {SHRINKWRAP} file"
                raise ValueError(msg)
            lock = NpmLock.model_validate_json(member.read())
        (candidate / "package.json").write_text(json.dumps(project(ARCHIVE, lock), indent=2) + "\n")
        npm = Path(work) / "npm"
        npm.mkdir()
        env = npm_env(npm)
        check_tools(tools, env)
        subprocess.run(NPM_INSTALL, cwd=candidate, env=env, capture_output=True, text=True, check=True)
        verified(candidate, want, reused=False)
        previous = target.with_name(PREVIOUS)
        if target.exists():
            target.rename(previous)
        candidate.rename(target)
    return verified(target, want, reused=False)


@contextlib.contextmanager
def settled(target: Path) -> Generator[None]:
    """Around the steps after a swap (patch, identity): on success remove the old folder; on any failure put it
    back in target's place. With no old folder, a failed step leaves target as it is, for rea-doctor to report."""
    previous = target.with_name(PREVIOUS)
    try:
        yield
    except BaseException:
        if previous.exists():
            shutil.rmtree(target)
            previous.rename(target)
        raise
    if previous.exists():
        shutil.rmtree(previous)


def run(package: str | None, url: str | None, want: ReaPin, tools: Mapping[str, str]) -> ReaFolder:
    """Keep a folder that already holds the pinned archive (its sha256 checked again) and a verified install, as a
    warm CI cache does; else install one."""
    target = folder()
    kept = target / ARCHIVE
    if kept.is_file() and sha256(kept) == want.package_sha256 and intact(target, want):
        return verified(target, want, reused=True)
    if package:
        return install(Path(package), target, want, tools)
    with tempfile.TemporaryDirectory() as tmp:
        return install(fetch(url or want.asset_url, Path(tmp) / ARCHIVE), target, want, tools)
