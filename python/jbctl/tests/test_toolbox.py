"""--ide: a Toolbox shell-script name to the running IDE, against a stand-in Toolbox and stand-in IDE processes."""

import shutil
from pathlib import Path

import pytest

from .conftest import Start, install, product_info, run, settings


def test_resolve_reports_the_running_ide(capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start) -> None:
    ide = start("--http", "--mcp")
    # The port the MCP plugin saved (it does when the default was busy, or the user set one).
    settings(toolbox / "fake-config", f"mcpServerPort={ide.ports[1]}")
    assert run(capsys, "resolve", "--ide", "fake") == (0, [{"ide": {
        "app": str(toolbox / "fake.app"),
        "product_code": "FK",
        "build": "263.1.2",
        "pid": ide.process.pid,
        "mcp_url": f"http://127.0.0.1:{ide.ports[1]}/stream",
    }}], "")  # fmt: skip
    assert run(capsys, "check-direct", "--ide", "fake") == (0, [{"tools": 3, "direct": True}], "")


def test_a_forced_port_wins_over_the_saved_one(capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start) -> None:
    ide = start("--mcp", "--http")
    config = toolbox / "fake-config"
    settings(config, f"mcpServerPort={ide.ports[1]}")
    # The user's own .vmoptions (Help > Edit Custom VM Options) comes after the app's.
    (config / "fake.vmoptions").write_text(f"-Didea.mcp.server.force.port={ide.ports[0]}\n")
    code, [event], _ = run(capsys, "resolve", "--ide", "fake")
    assert (code, event["ide"]["mcp_url"]) == (0, f"http://127.0.0.1:{ide.ports[0]}/stream")


@pytest.mark.parametrize(
    ("jvm", "saved", "port", "source"),
    [
        (["-Didea.platform.prefix=CLion"], [], 64362, "the CLion default"),
        # CLion's own mcpServer.xml holds only enableMcpServer while its port is the default.
        (["-Didea.platform.prefix=Python"], ["enableMcpServer=true"], 64462, "the Python default"),
        # The plugin's offset is 0 for a prefix it does not list, and for "idea", the prefix when none is set.
        ([], [], 64342, "the idea default"),
    ],
)
def test_otherwise_the_product_default_is_checked(  # noqa: PLR0913 - one parameter per input the port comes from
    *,
    capsys: pytest.CaptureFixture[str],
    toolbox: Path,
    start: Start,
    jvm: list[str],
    saved: list[str],
    port: int,
    source: str,
) -> None:
    product_info(toolbox / "fake.app", *jvm)
    if saved:
        settings(toolbox / "fake-config", *saved)
    # The stand-in listens elsewhere, so the default (whoever else holds it) is not this IDE's.
    ide = start("--mcp")
    error = run(capsys, "resolve", "--ide", "fake")[2]
    assert error == f"pid {ide.process.pid} has no MCP server on port {port} ({source})"


def test_a_port_that_does_not_answer_mcp_is_refused(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start
) -> None:
    ide = start("--http")
    settings(toolbox / "fake-config", f"mcpServerPort={ide.ports[0]}")
    source = toolbox / "fake-config/options/mcpServer.xml"
    error = run(capsys, "resolve", "--ide", "fake")[2]
    assert error == f"pid {ide.process.pid} has no MCP server on port {ide.ports[0]} ({source})"


def test_the_numbered_install_is_its_own_ide(capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start) -> None:
    """fake1 is the product's second install (Toolbox's clion1): the running fake.app is not it."""
    start("--mcp")
    error = run(capsys, "resolve", "--ide", "fake1")[2]
    assert error == f"0 running IDEs are from {toolbox / 'fake-2.app'}; want exactly one"


@pytest.mark.usefixtures("toolbox")
def test_an_unknown_name_lists_the_ides(capsys: pytest.CaptureFixture[str]) -> None:
    # Not listed: an install with no shell script, the non-IDE tool (no product code), and a channel that
    # state.json does not list.
    assert run(capsys, "resolve", "--ide", "nope")[2] == "Toolbox has 0 installs named nope; its IDEs are fake, fake1"


def test_two_installs_with_one_name_are_refused(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    install(toolbox / "toolbox", "fake-copy", toolbox / "fake.app", "fake")
    assert run(capsys, "resolve", "--ide", "fake")[2].startswith("Toolbox has 2 installs named fake")


def test_the_app_overrules_a_stale_toolbox_record(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    info = toolbox / "fake.app/Contents/Resources/product-info.json"
    info.write_text('{"productCode": "FK", "buildNumber": "263.9.9"}')
    error = run(capsys, "resolve", "--ide", "fake")[2]
    assert error.endswith("Toolbox records FK 263.1.2, its product-info.json says FK 263.9.9")


def test_two_running_from_one_app_are_refused(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    start("--mcp")
    start("--mcp")
    assert run(capsys, "resolve", "--ide", "fake")[2].startswith("2 running IDEs are from")


def test_check_direct_needs_an_ide_or_a_url(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(capsys, "check-direct") == (1, [], "check-direct needs --ide or --mcp-url")


def test_an_ide_name_is_a_script_name(capsys: pytest.CaptureFixture[str]) -> None:
    code, events, error = run(capsys, "resolve", "--ide", "../CLion")
    assert (code, events, "pattern" in error) == (1, [], True)


def test_the_user_vmoptions_file_follows_the_launcher(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start
) -> None:
    """Toolbox's <app>.vmoptions beside the bundle is the user file; then <config>/<launcher>.vmoptions is not read."""
    ide = start("--mcp", "--http")
    config = toolbox / "fake-config"
    config.mkdir()
    (config / "fake.vmoptions").write_text(f"-Didea.mcp.server.force.port={ide.ports[1]}\n")
    (toolbox / "fake.app.vmoptions").write_text(f"  -Didea.mcp.server.force.port={ide.ports[0]}  \n")
    code, [event], _ = run(capsys, "resolve", "--ide", "fake")
    assert (code, event["ide"]["mcp_url"]) == (0, f"http://127.0.0.1:{ide.ports[0]}/stream")


@pytest.mark.parametrize("quoted", [True, False])
def test_an_idea_config_path_option_moves_the_settings(
    capsys: pytest.CaptureFixture[str], toolbox: Path, start: Start, monkeypatch: pytest.MonkeyPatch, *, quoted: bool
) -> None:
    """-Didea.config.path wins over Toolbox's default, read as PathManager does: quotes stripped, ~/ is home."""
    monkeypatch.setenv("HOME", str(toolbox))
    ide = start("--mcp")
    settings(toolbox / "moved", f"mcpServerPort={ide.ports[0]}")
    value = f'"{toolbox}/moved/"' if quoted else "~/moved"
    product_info(toolbox / "fake.app", f"-Didea.config.path={value}")
    code, [event], _ = run(capsys, "resolve", "--ide", "fake")
    assert (code, event["ide"]["mcp_url"]) == (0, f"http://127.0.0.1:{ide.ports[0]}/stream")


def test_a_relative_idea_config_path_is_refused(capsys: pytest.CaptureFixture[str], toolbox: Path) -> None:
    """Relative to the IDE's working directory, which jbctl cannot know."""
    product_info(toolbox / "fake.app", "-Didea.config.path=config")
    error = run(capsys, "resolve", "--ide", "fake")[2]
    assert error.endswith("idea.config.path 'config' is relative; only an absolute or ~/ path can be resolved")


@pytest.mark.skipif(not shutil.which("jbax"), reason="jbax is not installed (mise run //swift:install)")
def test_a_helper_that_does_not_answer_is_one_failure_line(
    capsys: pytest.CaptureFixture[str], start: Start, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A hung helper (the real jbax, asked for the IDE's windows before stop, given no time) is one Failure line;
    the command it ran is left out."""
    start()
    monkeypatch.setenv("JBCTL_TIMEOUT", "0")
    assert run(capsys, "stop", "--ide", "fake") == (1, [], "a helper did not answer within 0 s")


# Not a number (with a quote and a newline: JBCTL_TIMEOUT is outside text, inert in the Failure line), out of range,
# or a float the wait would overflow on.
@pytest.mark.parametrize("raw", ['6"0\n', "-1", "nan", "inf", "1e309", "1e300"])
def test_a_timeout_jbctl_cannot_wait_is_one_failure_line(
    capsys: pytest.CaptureFixture[str], start: Start, monkeypatch: pytest.MonkeyPatch, raw: str
) -> None:
    start()
    monkeypatch.setenv("JBCTL_TIMEOUT", raw)
    assert run(capsys, "stop", "--ide", "fake") == (1, [], f"JBCTL_TIMEOUT is {raw!r}; want seconds from 0 to 86400")
