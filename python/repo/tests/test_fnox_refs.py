"""repotools fnox-refs through its command line, in real git repositories, against real fnox output."""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from repotools.cli import main
from tests import clean_git_env

REPO = Path(__file__).resolve().parents[3]
GLOBAL = "unix/home/.config/fnox/config.toml"
PROVIDER = '[providers.doppler_x]\ntype = "doppler"\nproject = "p"\nconfig = "c"\n'
PEM = "-----BEGIN RSA PRIVATE KEY-----\\nAAAA\\n-----END RSA PRIVATE KEY-----"


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    clean_git_env(monkeypatch, config=False)
    subprocess.run(["git", "init", "-q", tmp_path], check=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def add(root: Path, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    subprocess.run(["git", "-C", root, "add", "-f", "."], check=True)


def report(capsys: pytest.CaptureFixture[str]) -> tuple[int, list[dict[str, str]]]:
    try:
        main(["fnox-refs"])
        code = 0
    except SystemExit as stopped:
        code = int(str(stopped.code))
    return code, [json.loads(line) for line in capsys.readouterr().out.splitlines()]


def test_references_pass_in_every_fnox_file(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # The provider is in the global config; the other files use it by name, as agent-tools.toml does.
    add(
        repo,
        {
            GLOBAL: PROVIDER + '[secrets]\nA_KEY = { provider = "doppler_x", value = "A_KEY" }\n',
            "fnox.toml": '[secrets]\nB = { provider = "doppler_x", value = "B" }\n',
            "x/.config/fnox.ci.toml": '[profiles.p.secrets]\nC = { provider = "doppler_x", value = "C" }\n',
            # No value yet: the doppler_write placeholder's shape.
            "x/fnox.toml": '[secrets]\nD = { provider = "doppler_x", if_missing = "error" }\n',
        },
    )
    assert report(capsys) == (0, [])


# An upper-case value passes a name pattern but is not the entry's own name: a base32 seed, another key's name.
@pytest.mark.parametrize("value", [PEM, "JBSWY3DPEHPK3PXP", "OTHER_KEY", "k", "", 42])
def test_a_value_that_is_not_a_name_fails(repo: Path, capsys: pytest.CaptureFixture[str], value: object) -> None:
    add(repo, {GLOBAL: PROVIDER + f'[secrets]\nK = {{ provider = "doppler_x", value = {json.dumps(value)} }}\n'})
    assert report(capsys) == (1, [{"path": GLOBAL, "key": "secrets.K", "rule": "value-not-a-reference"}])


def test_findings_never_print_the_value(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {GLOBAL: PROVIDER + '[secrets]\nK = { provider = "doppler_x", value = "s3cr3t-value" }\n'})
    main_out = report(capsys)
    assert "s3cr3t" not in json.dumps(main_out)


def test_a_default_on_a_doppler_entry_fails(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"fnox.toml": PROVIDER + '[secrets]\nK = { provider = "doppler_x", value = "K", default = "K" }\n'})
    assert report(capsys) == (1, [{"path": "fnox.toml", "key": "secrets.K", "rule": "default-on-doppler"}])


def test_profile_providers_and_default_providers_count(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    text = (
        'default_provider = "doppler_top"\n'
        '[providers.doppler_top]\ntype = "doppler"\n'
        '[secrets]\nTOP = { value = "plain text" }\n'
        '[profiles.w]\ndefault_provider = "doppler_w"\n'
        '[profiles.w.providers.doppler_w]\ntype = "doppler"\n'
        '[profiles.w.secrets]\nW = { value = "plain text" }\n'
        '[profiles.v.secrets]\nV = { value = "plain text" }\n'
    )
    add(repo, {"fnox.toml": text})
    assert report(capsys) == (
        1,
        [
            {"path": "fnox.toml", "key": "secrets.TOP", "rule": "value-not-a-reference"},
            {"path": "fnox.toml", "key": "profiles.w.secrets.W", "rule": "value-not-a-reference"},
            {"path": "fnox.toml", "key": "profiles.v.secrets.V", "rule": "value-not-a-reference"},
        ],
    )


@pytest.mark.parametrize(
    "path", ["fnox.ci.toml", ".fnox.toml", ".fnox.ci.toml", ".config/fnox.toml", "a/fnox.local.toml", "imported.toml"]
)
def test_every_fnox_name_and_any_other_toml_is_checked(
    repo: Path, capsys: pytest.CaptureFixture[str], path: str
) -> None:
    # fnox.<profile>.toml is where `fnox set --profile ci` writes; an import can name any TOML file.
    add(repo, {GLOBAL: PROVIDER, path: '[secrets]\nK = { provider = "doppler_x", value = "plain text" }\n'})
    assert report(capsys) == (1, [{"path": path, "key": "secrets.K", "rule": "value-not-a-reference"}])


def test_a_toml_file_fnox_does_not_name_may_be_unreadable(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"notes/template.toml": "[unfinished\n", "fnox.toml": PROVIDER})
    assert report(capsys) == (0, [])


def test_other_providers_are_not_checked(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(
        repo,
        {
            GLOBAL: PROVIDER
            + '[providers.age]\ntype = "age"\n[secrets]\nT = { provider = "age", value = "cipher+/=" }\n',
            # Odd shapes fnox itself would refuse: skipped here, never a crash.
            "fnox.toml": 'profiles = 1\nproviders = 2\n[secrets]\nS = "plain"\n',
        },
    )
    assert report(capsys) == (0, [])


def test_a_link_in_the_index_is_not_read(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (repo / "fnox.toml").symlink_to("nowhere")
    subprocess.run(["git", "-C", repo, "add", "-f", "."], check=True)
    assert report(capsys) == (0, [])


def test_an_unreadable_file_names_itself(repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
    add(repo, {"fnox.toml": "[secrets\n"})
    with pytest.raises(SystemExit) as stopped:
        main(["fnox-refs"])
    assert stopped.value.code == 1
    assert json.loads(capsys.readouterr().err)["error"].startswith("fnox.toml: ")


def test_what_fnox_set_writes_for_a_doppler_provider_fails(
    repo: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The leak itself: the real fnox writes the value into the TOML, and the check refuses the result."""
    fnox = shutil.which("fnox")
    if fnox is None:
        pytest.skip("fnox is a global mise tool")
    add(repo, {"fnox.toml": PROVIDER})
    for name in [name for name in os.environ if name.startswith(("FNOX_", "DOPPLER_"))]:
        monkeypatch.delenv(name)
    monkeypatch.setenv("FNOX_CONFIG_DIR", str(repo / "no-global"))
    subprocess.run([fnox, "set", "LEAKED", "--provider", "doppler_x"], input="a-fake-value\n", text=True, check=True)
    subprocess.run(["git", "-C", repo, "add", "fnox.toml"], check=True)
    assert "a-fake-value" in (repo / "fnox.toml").read_text()
    assert report(capsys) == (1, [{"path": "fnox.toml", "key": "secrets.LEAKED", "rule": "value-not-a-reference"}])


def test_the_tracked_fnox_files_pass(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    clean_git_env(monkeypatch, config=False)
    monkeypatch.chdir(REPO)
    assert report(capsys) == (0, [])
