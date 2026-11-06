"""settings-open against a stand-in IDE process: what a user sees when the IDE's windows are unsafe."""

import shutil

import pytest

from .conftest import Start, run


@pytest.mark.skipif(not shutil.which("jbax"), reason="jbax is not installed (mise run //swift:install)")
@pytest.mark.usefixtures("toolbox")
def test_an_ide_without_a_project_window_is_refused(capsys: pytest.CaptureFixture[str], start: Start) -> None:
    """Real jbax reports the stand-in IDE's windows (it has none), and jbctl refuses rather than tries; jbax's own
    backgroundRisks test covers the other unsafe states."""
    start("mcp")
    code, events, error = run(capsys, "settings-open", "--ide", "fake", "--page", "Keymap")
    found = "0 project windows, 0 minimized, modal or unknown, 0 others"
    refusal = f"Settings may bring the IDE forward from this state ({found}); only visible project windows are safe"
    assert (code, events, error) == (1, [], refusal)
