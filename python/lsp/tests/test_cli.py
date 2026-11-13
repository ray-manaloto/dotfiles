"""The command line: each action's server argument, an unknown server, and how failures exit."""

import pytest

from .conftest import Lsp


@pytest.mark.parametrize(
    ("argv", "said"),
    [
        (["doctor", "typescript"], "doctor takes no server"),
        (["conflicts", "clangd"], "conflicts takes no server"),
        (["status"], "status takes one server"),
        (["remove"], "remove takes one server"),
        (["bogus", "typescript"], "argument action: invalid Action value: 'bogus'"),
    ],
)
def test_usage_errors_exit_2(lsp: Lsp, argv: list[str], said: str) -> None:
    result = lsp(*argv)
    assert (result.code, result.out) == (2, "")
    assert result.err.splitlines()[-1] == f"lsptools: error: {said}"


@pytest.mark.usefixtures("world")
def test_an_unknown_server_is_one_error_event(lsp: Lsp) -> None:
    result = lsp("status", "rust-analyzer")
    assert (result.code, result.out) == (2, "")
    assert result.error() == "no language server 'rust-analyzer' in lsptools/servers.json (known: typescript, clangd)"


def test_the_help_names_the_time_limit(lsp: Lsp) -> None:
    result = lsp("--help")
    assert result.code == 0
    assert "LSPTOOLS_COMMAND_SECONDS and LSPTOOLS_REQUEST_SECONDS, when set, limit each command" in " ".join(
        result.out.split()
    )
