"""rea-install with real npm on a local stand-in package: no registry, and no network but a loopback server."""

import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tomllib
from collections.abc import Iterator, Mapping
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from typing import Any

import httpx
import pytest

from jbctl import cli, rea, reainstall
from jbctl.models import ReaDoctor, ReaIdentity, ReaInstall, ReaPin

from .conftest import run
from .standin import serve

VERSION = reainstall.pin().package_version
# The node on this PATH and the npm beside it, which npm_env puts first: what the check passes; the task's own
# pins are tested apart.
_NODE = shutil.which("node")
assert _NODE
NODE_BIN = Path(_NODE).parent
HERE = {
    name: subprocess.check_output([NODE_BIN / name, "--version"], text=True).strip().removeprefix("v")
    for name in ("node", "npm")
}
SWIFT = "// the stand-in native UI helper\n"
# A shrinkwrap in rea's shape: an optional dependency (Frida's place) with its own subtree, a package another
# platform installs, a dev-only one, and a cycle.
LOCK: dict[str, Any] = {
    "packages": {
        "": {"dependencies": {"a": "1"}, "optionalDependencies": {"opt": "2", "elsewhere": "9"}},
        "node_modules/a": {"version": "1.0.0", "dependencies": {"shared": "1"}},
        "node_modules/shared": {"version": "1.1.0"},
        "node_modules/opt": {"version": "2.0.0", "dependencies": {"shared": "3", "deep": "1", "tool": "1"}},
        "node_modules/opt/node_modules/shared": {"version": "3.0.0", "dependencies": {"opt": "2"}},
        "node_modules/deep": {"version": "1.0.0", "optionalDependencies": {"native-other-os": "1"}},
        "node_modules/tool": {"version": "1.0.0", "dev": True},
    }
}


def tgz(path: Path, members: Mapping[str, bytes | None]) -> Path:
    """A gzipped tar of members: a file's bytes, or None for a folder."""
    with tarfile.open(path, "w:gz") as archive:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            if data is None:
                info.type = tarfile.DIRTYPE
                archive.addfile(info)
            else:
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
    return path


def package(
    path: Path,
    *,
    version: str = VERSION,
    lock: dict[str, Any] | None = LOCK,
    helper: str | None = SWIFT,
    bin_script: str | None = None,
) -> Path:
    """A stand-in rea package.tgz: package.json without dependencies, so npm reads only this file.

    Its bin/rea.js (npm links it to node_modules/.bin/rea) prints its version, or is bin_script.
    """
    meta = {"name": "rea-agents", "version": version, "bin": {"rea": "bin/rea.js"}}
    members: dict[str, bytes | None] = {
        "package/package.json": json.dumps(meta).encode(),
        "package/bin/rea.js": (bin_script or f"#!/usr/bin/env node\nconsole.log('{version}')\n").encode(),
    }
    if lock is not None:
        members[reainstall.SHRINKWRAP] = json.dumps(lock).encode()
    if helper is not None:
        members["package/bridge/native/ReaNativeUI.swift"] = helper.encode()
    return tgz(path, members)


def pin_for(archive: Path) -> ReaPin:
    """The packaged pin with archive's sha256: what a pin of that stand-in would hold."""
    return reainstall.pin().model_copy(update={"package_sha256": reainstall.sha256(archive)})


@pytest.fixture
def data_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    return tmp_path / "data/jbctl/rea"


@pytest.fixture
def served(tmp_path: Path) -> Path:
    return package(tmp_path / "served.tgz")


@pytest.fixture
def server(served: Path) -> Iterator[str]:
    """A loopback server: /asset redirects to /package.tgz, the served stand-in; anything else is 404."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/asset":
                self.send_response(302)
                self.send_header("Location", "/package.tgz")
                self.end_headers()
            elif self.path == "/package.tgz":
                self.send_response(200)
                self.end_headers()
                self.wfile.write(served.read_bytes())
            else:
                self.send_error(404)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 - the base class's name
            pass

    httpd = serve(Handler)
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def test_the_packaged_pin_parses() -> None:
    want = reainstall.pin()
    assert want.asset_url.endswith(f"/{want.release_tag}/package.tgz")


@pytest.mark.parametrize(
    ("value", "under_home"), [(None, True), ("", True), ("relative/data", True), ("/abs/data", False)]
)
def test_the_folder_follows_xdg_data_home(
    monkeypatch: pytest.MonkeyPatch, value: str | None, *, under_home: bool
) -> None:
    if value is None:
        monkeypatch.delenv("XDG_DATA_HOME", raising=False)
    else:
        monkeypatch.setenv("XDG_DATA_HOME", value)
    want = Path.home() / ".local/share/jbctl/rea" if under_home else Path("/abs/data/jbctl/rea")
    assert reainstall.folder() == want
    assert rea.installed_helper() == want / "node_modules/rea-agents/bridge/native/ReaNativeUI.swift"


def test_npm_env_inherits_only_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("npm_config_registry", "http://127.0.0.1:9")
    monkeypatch.setenv("NPM_CONFIG_CACHE", str(tmp_path))
    env = reainstall.npm_env(tmp_path)
    assert sorted(env) == ["HOME", "PATH", "TMPDIR", "npm_config_globalconfig", "npm_config_userconfig"]
    assert env["PATH"] == os.pathsep.join([str(NODE_BIN), os.environ["PATH"]])
    assert [p.read_text() for p in (tmp_path / "user", tmp_path / "global")] == ["", ""]
    assert list((tmp_path / "home").iterdir()) == []


def test_install_puts_the_package_in_place(tmp_path: Path, data_home: Path) -> None:
    archive = package(tmp_path / "package.tgz")
    done = reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert (done.version, done.reused) == (VERSION, False)
    assert Path(done.helper).read_text() == SWIFT
    project = json.loads((data_home / "package.json").read_text())
    assert project["dependencies"] == {"rea-agents": "file:package.tgz"}
    # The optional dependency's whole subtree, nested along each path, as npm reads it.
    assert project["overrides"] == {
        "rea-agents": {
            "opt": {
                ".": "2.0.0",
                "deep": {".": "1.0.0"},  # native-other-os has no lock entry: another platform's
                "shared": {".": "3.0.0"},  # the nested copy, found before the root's; its edge back to opt stops
            }
        }
    }
    assert reainstall.sha256(data_home / "package.tgz") == reainstall.sha256(archive)
    assert [p.name for p in data_home.parent.iterdir()] == ["rea"]  # no candidate or old folder left


def test_a_package_without_optional_dependencies_pins_nothing(tmp_path: Path, data_home: Path) -> None:
    archive = package(tmp_path / "package.tgz", lock={"packages": {"": {"dependencies": {"a": "1"}}}})
    reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert json.loads((data_home / "package.json").read_text())["overrides"] == {"rea-agents": {}}


def test_install_replaces_the_old_folder(tmp_path: Path, data_home: Path) -> None:
    archive = package(tmp_path / "package.tgz")
    reainstall.install(archive, data_home, pin_for(archive), HERE)
    (data_home / "stale").touch()
    with reainstall.settled(data_home):
        reainstall.install(archive, data_home, pin_for(archive), HERE)
        # The old folder waits beside the new one until the steps after the swap succeed.
        assert (data_home.with_name(reainstall.PREVIOUS) / "stale").exists()
    assert not (data_home / "stale").exists()
    assert [p.name for p in data_home.parent.iterdir()] == ["rea"]  # no previous folder left


def old_folder(data_home: Path) -> None:
    """A rea folder as rea-install leaves one, plus a marker file."""
    data_home.mkdir(parents=True)
    (data_home / "package.json").write_text(json.dumps({"dependencies": {"rea-agents": "file:package.tgz"}}))
    (data_home / "kept").touch()


@pytest.mark.parametrize("content", [None, "{not json", json.dumps({"dependencies": {"other": "1"}})])
def test_a_folder_rea_install_did_not_make_is_refused_and_kept(
    tmp_path: Path, data_home: Path, content: str | None
) -> None:
    data_home.mkdir(parents=True)
    if content is not None:
        (data_home / "package.json").write_text(content)
    archive = package(tmp_path / "package.tgz")
    with pytest.raises(ValueError, match=re.escape(f"{data_home} is not a rea folder that rea-install made")):
        reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert [p.name for p in data_home.iterdir()] == ([] if content is None else ["package.json"])


def test_a_previous_swaps_leftover_is_refused_and_kept(tmp_path: Path, data_home: Path) -> None:
    previous = data_home.with_name(reainstall.PREVIOUS)
    previous.mkdir(parents=True)
    (previous / "kept").touch()
    archive = package(tmp_path / "package.tgz")
    with pytest.raises(ValueError, match=re.escape(f"{previous} holds a rea folder from a swap that did not finish")):
        reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert [p.name for p in previous.iterdir()] == ["kept"]
    assert not data_home.exists()


@pytest.mark.parametrize(
    ("kind", "error"),
    [
        ("version", "rea-agents 0.0.1 with"),
        ("helper", "without node_modules/rea-agents/bridge/native/ReaNativeUI.swift"),
        ("no lock", "no package/npm-shrinkwrap.json file"),
    ],
)
def test_a_wrong_package_leaves_the_old_folder(tmp_path: Path, data_home: Path, kind: str, error: str) -> None:
    old_folder(data_home)
    archive = package(
        tmp_path / "package.tgz",
        version="0.0.1" if kind == "version" else VERSION,
        helper=None if kind == "helper" else SWIFT,
        lock=None if kind == "no lock" else LOCK,
    )
    with pytest.raises(ValueError, match=re.escape(error)):
        reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert sorted(p.name for p in data_home.iterdir()) == ["kept", "package.json"]
    assert [p.name for p in data_home.parent.iterdir()] == ["rea"]


def test_a_shrinkwrap_that_is_not_a_file_is_refused(tmp_path: Path, data_home: Path) -> None:
    archive = tgz(tmp_path / "package.tgz", {"package/package.json": b"{}", reainstall.SHRINKWRAP: None})
    with pytest.raises(ValueError, match=re.escape("no package/npm-shrinkwrap.json file")):
        reainstall.install(archive, data_home, pin_for(archive), HERE)


def test_an_npm_failure_is_raised_with_its_output(tmp_path: Path, data_home: Path) -> None:
    members = {"package/package.json": b"{not json", reainstall.SHRINKWRAP: b'{"packages": {"": {}}}'}
    archive = tgz(tmp_path / "package.tgz", members)
    with pytest.raises(subprocess.CalledProcessError) as failed:
        reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert failed.value.stderr
    assert not data_home.exists()


def test_a_folder_with_the_pinned_archive_is_kept(tmp_path: Path, data_home: Path) -> None:
    archive = package(tmp_path / "package.tgz")
    want = pin_for(archive)
    reainstall.install(archive, data_home, want, HERE)
    before = (data_home / "package-lock.json").stat().st_mtime_ns
    done = reainstall.run(None, "http://127.0.0.1:9/never", want, HERE)
    assert done.reused
    assert (data_home / "package-lock.json").stat().st_mtime_ns == before


def test_a_broken_folder_beside_the_pinned_archive_is_installed_again(tmp_path: Path, data_home: Path) -> None:
    archive = package(tmp_path / "package.tgz")
    want = pin_for(archive)
    reainstall.install(archive, data_home, want, HERE)
    (data_home / "node_modules/rea-agents/package.json").unlink()
    assert not reainstall.run(str(archive), None, want, HERE).reused
    assert (data_home / "node_modules/rea-agents/package.json").is_file()


def test_a_folder_with_another_archive_is_installed_again(tmp_path: Path, data_home: Path) -> None:
    old = package(tmp_path / "old.tgz", lock={"packages": {"": {}}})
    reainstall.install(old, data_home, pin_for(old), HERE)
    archive = package(tmp_path / "package.tgz")
    done = reainstall.run(str(archive), None, pin_for(archive), HERE)
    assert not done.reused
    assert reainstall.sha256(data_home / "package.tgz") == reainstall.sha256(archive)


def test_the_asset_is_downloaded_through_its_redirect(data_home: Path, served: Path, server: str) -> None:
    want = pin_for(served)
    assert reainstall.run(None, f"{server}/asset", want, HERE).version == VERSION
    assert (data_home / "package.tgz").is_file()


def test_the_pins_own_url_is_the_default(data_home: Path, served: Path, server: str) -> None:
    want = pin_for(served).model_copy(update={"asset_url": f"{server}/asset"})
    assert reainstall.run(None, None, want, HERE).version == VERSION
    assert reainstall.sha256(data_home / "package.tgz") == reainstall.sha256(served)


def test_a_missing_asset_is_an_http_error(data_home: Path, served: Path, server: str) -> None:
    want = pin_for(served)
    with pytest.raises(httpx.HTTPStatusError):
        reainstall.run(None, f"{server}/gone", want, HERE)
    assert not data_home.exists()


def test_the_command_refuses_an_archive_that_is_not_the_pins(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, data_home: Path
) -> None:
    archive = package(tmp_path / "package.tgz")
    code, events, error = run(capsys, "rea-install", "--package", str(archive))
    assert (code, events) == (1, [])
    assert error == f"{archive}: sha256 {reainstall.sha256(archive)} is not the pin's {reainstall.pin().package_sha256}"
    assert not data_home.exists()


def test_the_command_reports_an_unreachable_asset(capsys: pytest.CaptureFixture[str], data_home: Path) -> None:
    """A folder whose archive is not the pinned one is not kept: the command downloads, and fails here."""
    data_home.mkdir(parents=True)
    (data_home / "package.tgz").write_bytes(b"not the pinned archive")
    code, events, error = run(capsys, "rea-install", "--url", "http://127.0.0.1:9/asset")
    assert (code, events, bool(error)) == (1, [], True)
    assert (data_home / "package.tgz").read_bytes() == b"not the pinned archive"


def test_without_a_node_on_path_nothing_is_installed(
    tmp_path: Path, data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old_folder(data_home)
    archive = package(tmp_path / "package.tgz")
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    with pytest.raises(FileNotFoundError, match="node"):
        reainstall.install(archive, data_home, pin_for(archive), HERE)
    assert sorted(p.name for p in data_home.iterdir()) == ["kept", "package.json"]


def test_the_npm_beside_node_comes_before_another_npm_on_path(
    tmp_path: Path, data_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    other = tmp_path / "other"
    other.mkdir()
    (other / "npm").symlink_to("/usr/bin/false")  # another npm first on PATH, which fails if it is ever run
    monkeypatch.setenv("PATH", os.pathsep.join([str(other), os.environ["PATH"]]))
    archive = package(tmp_path / "package.tgz")
    assert reainstall.install(archive, data_home, pin_for(archive), HERE).version == VERSION
    assert (data_home / "node_modules/rea-agents/package.json").is_file()


def test_another_npm_on_path_is_refused_before_it_runs(tmp_path: Path, data_home: Path) -> None:
    archive = package(tmp_path / "package.tgz")
    with pytest.raises(ValueError, match=re.escape(f"npm {HERE['npm']} on PATH is not the task's 0.0.0")):
        reainstall.install(archive, data_home, pin_for(archive), {**HERE, "npm": "0.0.0"})
    assert not data_home.exists()


def test_the_task_passes_a_hostile_package_path_as_one_argument(tmp_path: Path) -> None:
    """The real task's shell line: quotes, $(...), backticks and a ; in the file name reach jbctl as one path."""
    hostile = tmp_path / """p "q" 'r' $(touch pwned) `touch pwned2`; touch pwned3.tgz"""
    package(hostile)
    jbctl = Path(reainstall.__file__).resolve().parents[2]
    # jbctl's rea folder moves to tmp_path; mise's own data folder, where its tools are installed, stays.
    mise_data = os.environ.get("MISE_DATA_DIR") or str(
        Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share") / "mise"
    )
    data_home = tmp_path / "data/jbctl/rea"
    done = subprocess.run(
        ["mise", "run", "//jbctl:rea-install", "--package", str(hostile)],
        cwd=jbctl,
        env={**os.environ, "MISE_DATA_DIR": mise_data, "XDG_DATA_HOME": str(tmp_path / "data")},
        capture_output=True,
        text=True,
        check=False,
    )
    # mise prefixes each line with the task's name; jbctl's failure line is the JSON after it.
    line = next(line for line in done.stderr.splitlines() if '{"error":' in line)
    failure = json.loads(line[line.index('{"error":') :])
    assert done.returncode != 0
    # The pin's sha256 refuses the stand-in, naming the path exactly as given.
    assert failure["error"].startswith(f"{hostile}: sha256 ")
    for folder in (jbctl, tmp_path, Path.cwd()):
        assert not [p.name for p in folder.iterdir() if p.name.startswith("pwned")]
    assert not data_home.exists()


@pytest.fixture
def patchable(tmp_path: Path, pristine: Path) -> Path:
    """A stand-in package whose helper is the real, unpatched one, which jbctl's patch fits."""
    return package(tmp_path / "patchable.tgz", helper=pristine.read_text())


def install_step(archive: Path) -> ReaInstall:
    return ReaInstall(package=str(archive))


def test_install_patches_the_helper_and_records_the_identity(
    capsys: pytest.CaptureFixture[str], data_home: Path, patchable: Path
) -> None:
    want = pin_for(patchable)
    cli.rea_step(install_step(patchable), want, HERE)
    helper = Path(json.loads(capsys.readouterr().out)["rea"]["helper"])
    assert rea.MARKER in helper.read_text()
    identity = ReaIdentity.model_validate_json((data_home / reainstall.IDENTITY).read_text())
    assert (identity.source_sha, identity.package_sha256) == (want.source_sha, want.package_sha256)
    assert identity.patch_sha256 == reainstall.patch_sha256()
    assert identity.node_version == HERE["node"]


def test_a_kept_install_keeps_its_identity(
    capsys: pytest.CaptureFixture[str], data_home: Path, patchable: Path
) -> None:
    want = pin_for(patchable)
    cli.rea_step(install_step(patchable), want, HERE)
    before = (data_home / reainstall.IDENTITY).read_text()
    cli.rea_step(install_step(patchable), want, HERE)
    assert json.loads(capsys.readouterr().out.splitlines()[-1])["rea"]["reused"]
    assert (data_home / reainstall.IDENTITY).read_text() == before


def test_a_kept_install_without_an_identity_gets_one(data_home: Path, patchable: Path) -> None:
    want = pin_for(patchable)
    reainstall.install(patchable, data_home, want, HERE)
    assert not (data_home / reainstall.IDENTITY).exists()
    cli.rea_step(install_step(patchable), want, HERE)
    assert (data_home / reainstall.IDENTITY).is_file()


@pytest.mark.usefixtures("data_home")
def test_the_doctor_passes_a_patched_install_and_only_warns_of_a_stray_global_one(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, patchable: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    want = pin_for(patchable)
    cli.rea_step(install_step(patchable), want, HERE)
    capsys.readouterr()
    prefix = tmp_path / "prefix"
    monkeypatch.setenv("npm_config_prefix", str(prefix))
    cli.rea_step(ReaDoctor(), want, HERE)
    clean = json.loads(capsys.readouterr().out)["doctor"]
    assert clean == {
        "ok": True,
        "pinned_source_sha": want.source_sha,
        "installed_source_sha": want.source_sha,
        "package_sha_match": True,
        "patch_marker": True,
        "version": VERSION,
        "version_match": True,
        "stray_global": False,
    }
    (prefix / "lib/node_modules/rea-agents").mkdir(parents=True)
    cli.rea_step(ReaDoctor(), want, HERE)
    assert json.loads(capsys.readouterr().out)["doctor"] == {**clean, "stray_global": True}


def test_the_doctor_fails_on_a_missing_folder(capsys: pytest.CaptureFixture[str], data_home: Path) -> None:
    code, events, error = run(capsys, "rea-doctor")
    assert (code, error) == (1, "")
    assert events[0]["doctor"] == {
        "ok": False,
        "pinned_source_sha": reainstall.pin().source_sha,
        "package_sha_match": False,
        "patch_marker": False,
        "version_match": False,
        "stray_global": events[0]["doctor"]["stray_global"],
    }
    assert not data_home.exists()


def test_the_doctor_fails_on_an_unpatched_install(
    capsys: pytest.CaptureFixture[str], data_home: Path, patchable: Path
) -> None:
    want = pin_for(patchable)
    reainstall.install(patchable, data_home, want, HERE)
    reainstall.record(data_home, want, HERE["node"], keep=False)
    with pytest.raises(SystemExit) as stop:
        cli.rea_step(ReaDoctor(), want, HERE)
    doctor = json.loads(capsys.readouterr().out)["doctor"]
    assert (stop.value.code, doctor["ok"], doctor["patch_marker"], doctor["version_match"]) == (1, False, False, True)


@pytest.mark.usefixtures("data_home")
def test_the_doctor_fails_on_another_source_or_package(capsys: pytest.CaptureFixture[str], patchable: Path) -> None:
    want = pin_for(patchable)
    cli.rea_step(install_step(patchable), want, HERE)
    capsys.readouterr()
    newer = want.model_copy(update={"source_sha": "0" * 40, "package_sha256": "1" * 64})
    with pytest.raises(SystemExit):
        cli.rea_step(ReaDoctor(), newer, HERE)
    doctor = json.loads(capsys.readouterr().out)["doctor"]
    assert (doctor["installed_source_sha"], doctor["package_sha_match"], doctor["ok"]) == (
        want.source_sha,
        False,
        False,
    )


def test_the_doctor_fails_on_another_version_or_a_rea_that_does_not_run(
    capsys: pytest.CaptureFixture[str], data_home: Path, patchable: Path
) -> None:
    want = pin_for(patchable)
    cli.rea_step(install_step(patchable), want, HERE)
    capsys.readouterr()
    with pytest.raises(SystemExit):
        cli.rea_step(ReaDoctor(), want.model_copy(update={"package_version": "0.0.1"}), HERE)
    assert json.loads(capsys.readouterr().out)["doctor"]["version"] == VERSION
    (data_home / "node_modules/.bin/rea").unlink()
    (data_home / "node_modules/.bin/rea").write_text("#!/usr/bin/env node\nprocess.exit(3)\n")
    (data_home / "node_modules/.bin/rea").chmod(0o755)
    with pytest.raises(SystemExit):
        cli.rea_step(ReaDoctor(), want, HERE)
    doctor = json.loads(capsys.readouterr().out)["doctor"]
    assert (doctor["version_match"], "version" in doctor) == (False, False)
    (data_home / "node_modules/.bin/rea").unlink()
    with pytest.raises(SystemExit):
        cli.rea_step(ReaDoctor(), want, HERE)
    assert "version" not in json.loads(capsys.readouterr().out)["doctor"]


def test_a_patch_that_does_not_fit_puts_the_old_install_back(tmp_path: Path, data_home: Path, patchable: Path) -> None:
    """The old folder waits beside the new one until the new one is patched and recorded, so an upstream helper the
    patch no longer fits leaves the working install in place, not an unpatched one."""
    cli.rea_step(install_step(patchable), pin_for(patchable), HERE)
    before = {name: (data_home / name).read_bytes() for name in (reainstall.IDENTITY, reainstall.HELPER)}
    changed = package(tmp_path / "changed.tgz", helper=SWIFT)
    with pytest.raises(rea.IdeError, match="changed upstream"):
        cli.rea_step(install_step(changed), pin_for(changed), HERE)
    assert {name: (data_home / name).read_bytes() for name in before} == before
    assert reainstall.sha256(data_home / reainstall.ARCHIVE) == reainstall.sha256(patchable)
    assert [p.name for p in data_home.parent.iterdir()] == ["rea"]  # no previous folder left


def test_a_first_install_whose_patch_does_not_fit_is_left_unpatched(tmp_path: Path, data_home: Path) -> None:
    """With no old folder to put back, the new one stays, unpatched and with no identity, for rea-doctor to fail."""
    changed = package(tmp_path / "changed.tgz", helper=SWIFT)
    with pytest.raises(rea.IdeError):
        cli.rea_step(install_step(changed), pin_for(changed), HERE)
    assert (data_home / reainstall.HELPER).read_text() == SWIFT
    assert not (data_home / reainstall.IDENTITY).exists()
    assert [p.name for p in data_home.parent.iterdir()] == ["rea"]


@pytest.mark.parametrize("broken", ["node_modules/.bin/rea", "node_modules/rea-agents/package.json"])
def test_a_folder_missing_its_rea_or_with_an_unreadable_package_json_is_installed_again(
    tmp_path: Path, data_home: Path, broken: str
) -> None:
    archive = package(tmp_path / "package.tgz")
    want = pin_for(archive)
    reainstall.install(archive, data_home, want, HERE)
    if broken.endswith(".json"):
        (data_home / broken).write_text("{not json")
    else:
        (data_home / broken).unlink()
    assert not reainstall.run(str(archive), None, want, HERE).reused
    assert (data_home / "node_modules/.bin/rea").is_file()


def test_only_rea_install_reads_the_task_tools(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, pristine: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An installed jbctl has no mise.toml beside it: rea-patch and rea-doctor still run, and rea-install says how to
    run it."""
    monkeypatch.setattr(reainstall, "TASKS", tmp_path / "absent/mise.toml")
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    assert run(capsys, "rea-patch", "--helper", str(pristine)) == (0, [{"patch": "applied"}], "")
    code, _, error = run(capsys, "rea-doctor")
    assert (code, error) == (1, "")
    code, events, error = run(capsys, "rea-install")
    assert (code, events) == (1, [])
    assert "mise run //jbctl:rea-install" in error


def test_the_test_tasks_install_rea_first() -> None:
    """The offline tests copy the installed helper, so every task that runs them installs it first."""
    tasks = tomllib.loads((Path(__file__).parents[1] / "mise.toml").read_text())["tasks"]
    for name in ("test", "coverage"):
        assert "rea-install" in tasks[name]["depends"], name
