"""Every test runs outside the repository a git hook exported."""

import pytest

from tests import drop_repo_git_env


@pytest.fixture(autouse=True)
def no_repo_git_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every test starts outside any repository a hook exported; see drop_repo_git_env."""
    drop_repo_git_env(monkeypatch)
