"""depmaps end to end: the installed command against a real git repository and the real cbm."""

import json
import subprocess

import pytest

from .conftest import CBM, Env, cbm_tool, database, events, git, release


def done(result: str) -> dict[str, str]:
    return events(result)[-1]


def errors(text: str) -> list[tuple[str, str]]:
    return [(each["code"], each["message"]) for each in events(text)]


@pytest.mark.parametrize(
    "args",
    [[], ["nope"], ["list", "extra"], ["map"], ["map", "x", "--version"], ["map", "x", "--version", "../up"],
     ["diff", "x", "1.0.0"]],
)  # fmt: skip
def test_usage(env: Env, args: list[str]) -> None:
    result = env.run(*args)
    assert result.returncode == 2
    assert result.stdout == ""
    [error] = events(result.stderr)
    assert error["code"] == "invalid_usage"
    assert error["message"].startswith("usage: depmaps list | map <dep>")


def test_registry_errors(env: Env) -> None:
    env.registry.write_text('{"deps": {"Bad_Name": {}}}')
    result = env.run("list")
    assert result.returncode == 1
    [(code, _)] = errors(result.stderr)
    assert code == "invalid_registry"
    assert done(result.stdout) == {
        "event": "done",
        "command": "list",
        "message": "depmaps: list failed: invalid_registry",
    }
    env.registry.unlink()
    assert errors(env.run("sync").stderr)[0][0] == "invalid_registry"
    env.deps({env.name: env.dep()})
    result = env.run("map", "other")
    assert result.returncode == 1
    assert errors(result.stderr) == [("unknown_dep", "depmaps: other is not in the registry")]


def mise_version() -> str:
    """What the registry's mise entry reads: the first field of mise's own version line."""
    found = subprocess.run(["mise", "--version"], capture_output=True, text=True, check=True, timeout=30)
    return found.stdout.split()[0]


def test_list_versions(env: Env) -> None:
    env.deps({env.name: env.dep(), "by-command": env.dep(version={"command": ["mise", "--version"]})})
    result = env.run("list")
    assert result.returncode == 0, result.stderr
    assert events(result.stdout) == [
        {"event": "dep", "dep": env.name, "version": "1.0.0", "mapped": False},
        {"event": "dep", "dep": "by-command", "version": mise_version(), "mapped": False},
        {"event": "done", "command": "list", "message": "depmaps: 2 deps, 0 mapped at the pinned version"},
    ]


def test_version_failures(env: Env) -> None:
    env.lock.write_text(
        '[[tools."twice"]]\nversion = "1.0.0"\n[[tools."twice"]]\nversion = "1.1.0"\n'
        '[[tools."unversioned"]]\nbackend = "x"\n'
    )  # fmt: skip
    env.deps({
        "not-locked": env.dep(version={"lock": "fixture:tool"}),
        "twice": env.dep(version={"lock": "twice"}),
        "unversioned": env.dep(version={"lock": "unversioned"}),
        "no-program": env.dep(version={"command": [str(env.root / "missing")]}),
        "exits": env.dep(version={"command": ["false"]}),
        "silent": env.dep(version={"command": ["true"]}),
        "odd": env.dep(version={"command": ["echo", "../1.0"]}),
        "bare-clone": env.dep(version={"command": ["echo", ".repo.git"]}),
        "fine": env.dep(version={"command": ["mise", "--version"]}),
    })  # fmt: skip
    result = env.run("list")
    assert result.returncode == 1
    codes = errors(result.stderr)
    assert [code for code, _ in codes] == ["version_unavailable"] * 8
    messages = [message for _, message in codes]
    assert messages[0].endswith("needs one version of fixture:tool, found none")
    assert messages[1].endswith("needs one version of twice, found 1.0.0, 1.1.0")
    assert messages[2].endswith("needs one version of unversioned, found none")
    assert "No such file or directory" in messages[3]
    assert "exited 1" in messages[4]
    assert "exited 0 with ''" in messages[5]
    assert messages[6].endswith("gave '../1.0', not a version")
    assert messages[7].endswith("gave '.repo.git', not a version")
    assert events(result.stdout) == [
        {"event": "dep", "dep": "fine", "version": mise_version(), "mapped": False},
        {"event": "done", "command": "list", "message": "depmaps: 9 deps, 0 mapped at the pinned version; 8 failed"},
    ]
    env.lock.unlink()
    env.deps({env.name: env.dep()})
    [(code, message)] = errors(env.run("list").stderr)
    assert code == "version_unavailable"
    assert f"lockfile {env.lock}" in message


def cbm_version() -> str:
    found = subprocess.run([str(CBM), "--version"], capture_output=True, text=True, check=True, timeout=30)
    return found.stdout.split()[-1]


def test_map(env: Env) -> None:
    result = env.run("map", env.name)
    assert result.returncode == 0, result.stderr
    [mapped, end] = events(result.stdout)
    manifest = mapped["manifest"]
    commit = git(env.repo, "rev-parse", "v1.0.0^{commit}").strip()
    project = f"{env.name}-v1.0.0"
    assert manifest | {"indexed_at": "", "nodes": 0, "edges": 0, "schema_version": 0} == {
        "dep": env.name, "version": "1.0.0", "tag": "v1.0.0", "commit": commit, "project": project,
        "cbm_version": cbm_version(), "schema_version": 0, "indexed_at": "", "nodes": 0, "edges": 0,
    }  # fmt: skip
    assert manifest["nodes"] > 0
    assert manifest["edges"] > 0
    assert end == {"event": "done", "command": "map", "message": f"depmaps: mapped {env.name} 1.0.0"}
    folder = env.folder("1.0.0")
    assert json.loads((folder / "manifest.json").read_text()) == manifest
    assert git(folder / "src", "rev-parse", "HEAD").strip() == commit
    assert (folder / "src/.codebase-memory/artifact.json").is_file()
    assert database(project).is_file()
    listed = events(env.run("list").stdout)
    assert listed[0] == {"event": "dep", "dep": env.name, "version": "1.0.0", "mapped": True}
    # Mapping a version again rebuilds it from nothing.
    again = env.run("map", env.name, "--version", "1.0.0")
    assert again.returncode == 0, again.stderr
    assert events(again.stdout)[0]["manifest"]["commit"] == commit


def test_map_finishes_a_map_cut_short(env: Env) -> None:
    env.folder("1.1.0").mkdir(parents=True)
    (env.folder("1.1.0") / "partial").write_text("")
    result = env.run("map", env.name, "--version", "1.1.0")
    assert result.returncode == 0, result.stderr
    assert sorted(path.name for path in env.folder("1.1.0").iterdir()) == ["manifest.json", "src"]


def test_map_fetches_a_later_tag(env: Env) -> None:
    assert env.run("map", env.name).returncode == 0
    release(env.repo, "1.3.0", {"notes.md": "four\n"})
    result = env.run("map", env.name, "--version", "1.3.0")
    assert result.returncode == 0, result.stderr
    assert events(result.stdout)[0]["manifest"]["tag"] == "v1.3.0"
    missing = env.run("map", env.name, "--version", "9.9.9")
    assert missing.returncode == 1
    assert errors(missing.stderr) == [("version_unavailable", f"depmaps: {env.repo} has no tag v9.9.9")]
    assert done(missing.stdout)["message"] == "depmaps: map failed: version_unavailable"


def test_map_git_failures(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    env.deps({env.name: env.dep(repo=str(env.root / "no-such-repo"))})
    [(code, message)] = errors(env.run("map", env.name).stderr)
    assert code == "git_failed"
    assert message.startswith("depmaps: git clone --bare --quiet")
    monkeypatch.setenv("PATH", str(env.root / "empty"))
    [(code, message)] = errors(env.run("map", env.name).stderr)
    assert code == "git_failed"
    assert "No such file or directory" in message


@pytest.mark.parametrize(
    ("cbm", "expected"),
    [
        ("missing", "No such file or directory"),
        ("false", "--version exited 1"),
        ("git", "cbm index_repository exited 1"),
    ],
)  # fmt: skip
def test_cbm_failures(env: Env, monkeypatch: pytest.MonkeyPatch, cbm: str, expected: str) -> None:
    # false and git are real programs: one fails `--version`, the other answers it and fails the index.
    monkeypatch.setenv("DEP_MAPS_CBM", str(env.root / cbm) if cbm == "missing" else cbm)
    result = env.run("map", env.name)
    assert result.returncode == 1
    [(code, message)] = errors(result.stderr)
    assert code == "cbm_failed"
    assert expected in message
    assert not (env.folder("1.0.0") / "manifest.json").exists()


def test_sync_and_prune(env: Env) -> None:
    first = env.run("sync")
    assert first.returncode == 0, first.stderr
    assert [each["event"] for each in events(first.stdout)] == ["mapped", "done"]
    assert done(first.stdout)["message"] == "depmaps: sync mapped 1, pruned 0"
    second = env.run("sync")
    assert events(second.stdout) == [
        {"event": "done", "command": "sync", "message": "depmaps: sync mapped 0, pruned 0"}
    ]
    # A folder with no manifest.json is not a depmaps map, such as an earlier prototype's: never touched.
    (env.folder("v1.0.0-proto") / "src").mkdir(parents=True)
    env.pin("1.1.0")
    assert done(env.run("sync").stdout)["message"] == "depmaps: sync mapped 1, pruned 0"
    env.pin("1.2.0")
    third = env.run("sync")
    assert third.returncode == 0, third.stderr
    assert events(third.stdout)[1:] == [
        {"event": "pruned", "dep": env.name, "version": "1.0.0"},
        {"event": "done", "command": "sync", "message": "depmaps: sync mapped 1, pruned 1"},
    ]
    assert sorted(path.name for path in (env.store / env.name).iterdir()) == [
        ".repo.git",
        "1.1.0",
        "1.2.0",
        "v1.0.0-proto",
    ]
    assert not database(f"{env.name}-v1.0.0").exists()
    assert database(f"{env.name}-v1.1.0").is_file()
    worktrees = git(env.store / env.name / ".repo.git", "worktree", "list", "--porcelain")
    assert str(env.folder("1.0.0")) not in worktrees
    assert str(env.folder("1.1.0") / "src") in worktrees


def test_prune_keeps_the_version_below_the_pin(env: Env) -> None:
    # Built out of order, 1.10.0 before 1.9.0, and as text 1.10.0 sorts before 1.9.0: either order would
    # keep 1.9.0, which comes before 1.10.0.
    for version in ("1.9.0", "1.10.0", "1.11.0"):
        release(env.repo, version, {"notes.md": f"{version}\n"})
    for version in ("1.10.0", "1.9.0"):
        assert env.run("map", env.name, "--version", version).returncode == 0
    env.pin("1.11.0")
    result = env.run("sync")
    assert result.returncode == 0, result.stderr
    assert events(result.stdout)[1:] == [
        {"event": "pruned", "dep": env.name, "version": "1.9.0"},
        {"event": "done", "command": "sync", "message": "depmaps: sync mapped 1, pruned 1"},
    ]
    assert database(f"{env.name}-v1.10.0").is_file()
    # With 1.9.0 mapped again, the pin moves back to 1.10.0: 1.11.0, newer than the pin, goes, and 1.9.0,
    # the one below it, stays.
    assert env.run("map", env.name, "--version", "1.9.0").returncode == 0
    env.pin("1.10.0")
    result = env.run("sync")
    assert result.returncode == 0, result.stderr
    assert events(result.stdout) == [
        {"event": "pruned", "dep": env.name, "version": "1.11.0"},
        {"event": "done", "command": "sync", "message": "depmaps: sync mapped 0, pruned 1"},
    ]
    assert database(f"{env.name}-v1.9.0").is_file()


def test_sync_rebuilds_a_map_cbm_lost(env: Env) -> None:
    assert env.run("sync").returncode == 0
    assert cbm_tool("delete_project", {"project": f"{env.name}-v1.0.0"}).returncode == 0
    assert (env.folder("1.0.0") / "manifest.json").exists()
    assert events(env.run("list").stdout)[0]["mapped"] is False
    result = env.run("sync")
    assert result.returncode == 0, result.stderr
    assert done(result.stdout)["message"] == "depmaps: sync mapped 1, pruned 0"
    assert database(f"{env.name}-v1.0.0").is_file()
    assert events(env.run("list").stdout)[0]["mapped"] is True


def test_sync_goes_on_after_a_failure(env: Env) -> None:
    env.deps({"broken": env.dep(repo=str(env.root / "no-such-repo")), env.name: env.dep()})
    result = env.run("sync")
    assert result.returncode == 1
    assert [code for code, _ in errors(result.stderr)] == ["git_failed"]
    assert [each["event"] for each in events(result.stdout)] == ["mapped", "done"]
    assert done(result.stdout)["message"] == "depmaps: sync mapped 1, pruned 0; 1 failed"


@pytest.mark.parametrize("damage", ["not json", "folder", "other map"])
def test_invalid_manifest_is_an_error(env: Env, damage: str) -> None:
    assert env.run("map", env.name).returncode == 0
    path = env.folder("1.0.0") / "manifest.json"
    if damage == "folder":
        path.unlink()
        path.mkdir()
    else:
        text = path.read_text()
        path.write_text("{" if damage == "not json" else text.replace(f'"{env.name}"', '"another"'))
    for command in ("list", "sync"):
        result = env.run(command)
        assert result.returncode == 1, result.stdout
        error = events(result.stderr)[0]
        assert error["code"] == "invalid_manifest"
        assert str(path) in error["message"]
        assert done(result.stdout)["message"].endswith("; 1 failed")
    assert path.exists(), "an invalid manifest is reported, never rebuilt over"


def test_diff(env: Env) -> None:
    for version in ("1.0.0", "1.1.0"):
        assert env.run("map", env.name, "--version", version).returncode == 0
    result = env.run("diff", env.name, "1.0.0", "1.1.0")
    assert result.returncode == 0, result.stderr
    summary = "4 functions, 4 files changed"

    def change(kind: str, name: str, before: str | None = None, after: str | None = None) -> dict[str, str | None]:
        fields = {"kind": kind, "label": "Function", "file": "core.py", "name": name}
        return {"event": "change", **fields, "before": before, "after": after}

    assert events(result.stdout) == [
        change("added", "core.fresh"),
        change("removed", "core.gone"),
        change("signature", "core.shape", "(a)", "(a, b)"),
        change("body", "core.tiny"),
        {"event": "file", "status": "R100", "path": "schema/b.json"},
        {"event": "file", "status": "A", "path": "schema/new.json"},
        {"event": "file", "status": "D", "path": "schema/old.json"},
        {"event": "file", "status": "M", "path": "settings.toml"},
        {"event": "done", "command": "diff", "message": f"depmaps: {env.name} 1.0.0 -> 1.1.0: {summary}"},
    ]  # fmt: skip
    env.deps({env.name: env.dep()})
    plain = env.run("diff", env.name, "1.0.0", "1.1.0")
    assert [each["event"] for each in events(plain.stdout)] == ["change"] * 4 + ["done"]


def test_diff_reads_quoted_and_spaced_names(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    # git ends a `+++` line with a tab when the name has a space, and C-quotes a name with a quote or
    # a non-ASCII byte. Each tiny function changes only its body, which cbm doesn't hash, so only the
    # git hunk in its file can show the change. The registry lists every file, and one name is renamed.
    names = ["say hi.py", 'say "hi".py', "caf\u00e9.py", 'say "caf\u00e9".py']
    old, new = 'old "caf\u00e9".toml', 'new "caf\u00e9".toml'
    release(env.repo, "1.3.0", dict.fromkeys(names, "def tiny():\n    return 1\n") | {old: "a = 1\n"})
    release(env.repo, "1.4.0", dict.fromkeys(names, "def tiny():\n    return 2\n") | {old: None, new: "a = 1\n"})
    env.deps({env.name: env.dep(files=["*.py", "*.toml"])})
    for version in ("1.3.0", "1.4.0"):
        assert env.run("map", env.name, "--version", version).returncode == 0
    # Settings that change the `+++` line, as a user's git config could set them.
    settings = {"core.quotePath": "false", "diff.noprefix": "true", "diff.mnemonicPrefix": "true"}
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(settings)))
    for index, (key, value) in enumerate(settings.items()):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{index}", key)
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{index}", value)
    result = env.run("diff", env.name, "1.3.0", "1.4.0")
    assert result.returncode == 0, result.stderr
    found = events(result.stdout)[:-1]
    changed = [(each["kind"], each["file"], each["name"]) for each in found if each["event"] == "change"]
    assert sorted(changed) == sorted(("body", name, f"{name.removesuffix('.py')}.tiny") for name in names)
    listed = [(each["status"], each["path"]) for each in found if each["event"] == "file"]
    assert sorted(listed) == sorted([("R100", new)] + [("M", name) for name in names])


def test_diff_reads_an_added_line_that_looks_like_a_header(env: Env) -> None:
    # The added line `++ count;` shows as `+++ count;` inside its hunk. It names no file, so the next
    # hunk, in g, still belongs to count.c. Both bodies are too small for cbm to hash.
    before = "int f(int count) {\n    return count;\n}\n\nint g(void) {\n    return 1;\n}\n"
    after = "int f(int count) {\n++ count;\n    return count;\n}\n\nint g(void) {\n    return 2;\n}\n"
    release(env.repo, "1.3.0", {"count.c": before})
    release(env.repo, "1.4.0", {"count.c": after})
    for version in ("1.3.0", "1.4.0"):
        assert env.run("map", env.name, "--version", version).returncode == 0
    result = env.run("diff", env.name, "1.3.0", "1.4.0")
    assert result.returncode == 0, result.stderr
    changed = [each for each in events(result.stdout) if each["event"] == "change"]
    assert sorted((each["kind"], each["file"], each["name"].rsplit(".", 1)[-1]) for each in changed) == [
        ("body", "count.c", "f"),
        ("body", "count.c", "g"),
    ]


def test_a_relative_store_is_read_from_the_working_folder(env: Env, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DEP_MAPS_STORE", env.store.name)
    assert env.run("map", env.name).returncode == 0
    assert (env.folder("1.0.0") / "manifest.json").exists()
    assert events(env.run("list").stdout)[0]["mapped"] is True


def test_diff_needs_both_maps(env: Env) -> None:
    assert env.run("map", env.name).returncode == 0
    result = env.run("diff", env.name, "1.0.0", "1.1.0")
    assert result.returncode == 1
    message = f"depmaps: {env.name} 1.1.0 has no map; mise run //depmaps:map {env.name}"
    assert errors(result.stderr) == [("no_map", message)]
    assert env.run("map", env.name, "--version", "1.1.0").returncode == 0
    assert json.loads(cbm_tool("delete_project", {"project": f"{env.name}-v1.0.0"}).stdout)["status"] == "deleted"
    [(code, message)] = errors(env.run("diff", env.name, "1.0.0", "1.1.0").stderr)
    assert code == "no_map"
    assert message.startswith(f"depmaps: cbm map {database(env.name + '-v1.0.0')}")


def test_sync_reads_the_global_lockfile_from_any_folder(env: Env) -> None:
    # A folder whose own mise config pins another version: the lockfile depmaps reads is still the global one.
    other = env.root / "project"
    other.mkdir()
    (other / "mise.toml").write_text('[tools]\n"fixture:tool" = "1.1.0"\n')
    (other / "mise.lock").write_text('[[tools."fixture:tool"]]\nversion = "1.1.0"\n')
    result = env.run("list", cwd=other)
    assert events(result.stdout)[0]["version"] == "1.0.0"
