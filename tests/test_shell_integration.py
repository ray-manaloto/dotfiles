"""Tests for shell integration and tool reachability in login shells."""

import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).parent.parent

# The gpg-agent SSH-override guard is duplicated in the bash and zsh
# rc templates. It must fire ONLY when gpg-agent has ssh-support enabled;
# a wrong predicate silently rebinds SSH_AUTH_SOCK and breaks every SSH
# workflow (1Password, macOS Keychain, Docker Desktop's magic socket).
# Regression test for issue #87 (S1 from the PR #86 review).
_SHELL_RC_TEMPLATES = ["dot_bashrc.tmpl", "dot_zshrc.tmpl"]

# Capture the literal shell block from the template: from the guard's
# opening `if command -v gpgconf` to the first column-0 `fi` (the inner
# `  fi` is indented, so `^fi$` cannot match it). The surrounding
# chezmoi `{{if not .remote}}` conditionals sit OUTSIDE this block, so
# the captured text is pure shell.
_GPG_GUARD_RE = re.compile(
    r"^(if command -v gpgconf\b.*?^fi)$", re.MULTILINE | re.DOTALL
)


def _extract_gpg_guard(template_name: str) -> str:
    text = (_REPO_ROOT / "home" / template_name).read_text()
    match = _GPG_GUARD_RE.search(text)
    assert match is not None, f"gpg-agent guard block not found in {template_name}"
    return match.group(1)


# Sentinel socket path the gpgconf shim reports for agent-ssh-socket.
# Not under /tmp (so no hardcoded-temp lint) and never created on disk —
# the guard only reads it as a string to assign to SSH_AUTH_SOCK.
_AGENT_SOCK_BASENAME = "fake-gpg-agent-ssh.sock"


def _run_guard(
    guard: str, *, gpgconf_present: bool, ssh_support_enabled: bool, orig_sock: str
) -> str:
    """Run the extracted guard under a hermetic PATH and return SSH_AUTH_SOCK.

    PATH is restricted to a temp dir holding only a `grep` symlink (the
    guard's one external dependency) and, optionally, a `gpgconf` shim —
    so `command -v gpgconf` resolves deterministically regardless of
    whether the host actually has gpgconf installed.
    """
    bash = shutil.which("bash")
    grep = shutil.which("grep")
    assert bash, "bash is required to run this test"
    assert grep, "grep is required to run this test"

    with tempfile.TemporaryDirectory() as tmp:
        bin_dir = Path(tmp) / "bin"
        bin_dir.mkdir()
        (bin_dir / "grep").symlink_to(grep)
        agent_sock = str(Path(tmp) / _AGENT_SOCK_BASENAME)

        if gpgconf_present:
            # Absolute-path shebang so the shim runs under the restricted
            # PATH (an `/usr/bin/env bash` shebang would fail to find bash).
            value = "1" if ssh_support_enabled else "0"
            shim = bin_dir / "gpgconf"
            shim.write_text(
                "#!/bin/sh\n"
                'if [ "$1" = "--list-options" ]; then\n'
                f'  echo "enable-ssh-support:0:{value}"\n'
                'elif [ "$1" = "--list-dirs" ]; then\n'
                f'  echo "{agent_sock}"\n'
                "fi\n"
            )
            # Owner-only exec — the test process is the only caller.
            shim.chmod(0o700)

        script = f'{guard}\nprintf "%s" "$SSH_AUTH_SOCK"'
        env = {"PATH": str(bin_dir), "SSH_AUTH_SOCK": orig_sock}
        result = subprocess.run(
            [bash, "-c", script],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"guard errored: {result.stderr}"
        return result.stdout


@pytest.mark.parametrize("template_name", _SHELL_RC_TEMPLATES)
def test_gpg_guard_no_clobber_when_gpgconf_absent(template_name: str) -> None:
    """Gpgconf absent → SSH_AUTH_SOCK MUST be untouched."""
    guard = _extract_gpg_guard(template_name)
    orig = "/original/agent.sock"
    out = _run_guard(
        guard, gpgconf_present=False, ssh_support_enabled=False, orig_sock=orig
    )
    assert out == orig, (
        f"{template_name}: guard clobbered SSH_AUTH_SOCK with gpgconf absent"
    )


@pytest.mark.parametrize("template_name", _SHELL_RC_TEMPLATES)
def test_gpg_guard_no_clobber_when_ssh_support_disabled(template_name: str) -> None:
    """Gpgconf present but ssh-support disabled → SSH_AUTH_SOCK untouched.

    This is the exact regression the guard's predicate exists to prevent
    (an earlier session burned hours on a silent override here).
    """
    guard = _extract_gpg_guard(template_name)
    orig = "/original/agent.sock"
    out = _run_guard(
        guard, gpgconf_present=True, ssh_support_enabled=False, orig_sock=orig
    )
    assert out == orig, (
        f"{template_name}: guard clobbered SSH_AUTH_SOCK despite ssh-support disabled"
    )


@pytest.mark.parametrize("template_name", _SHELL_RC_TEMPLATES)
def test_gpg_guard_overrides_when_ssh_support_enabled(template_name: str) -> None:
    """Gpgconf present AND ssh-support enabled → override fires (positive case)."""
    guard = _extract_gpg_guard(template_name)
    orig = "/original/agent.sock"
    out = _run_guard(
        guard, gpgconf_present=True, ssh_support_enabled=True, orig_sock=orig
    )
    assert out != orig, f"{template_name}: override did not fire (got {out!r})"
    assert out.endswith(_AGENT_SOCK_BASENAME), (
        f"{template_name}: SSH_AUTH_SOCK not set to gpg-agent socket (got {out!r})"
    )


# We parametrize with the tools we expect to be in the PATH
@pytest.mark.parametrize(
    "tool", ["mise", "chezmoi", "uv", "pixi", "claude", "gemini", "codex"]
)
def test_tool_reachable_in_login_shell(tool: str) -> None:
    """Verify tools are reachable in a login shell."""
    # Use bash -l to simulate a login shell
    cmd = ["bash", "-l", "-c", f"which {tool}"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Assert tool is found
    assert result.returncode == 0, (
        f"{tool} not found in login shell PATH. Stderr: {result.stderr}"
    )

    # Verify the path resolves to a real binary (not empty)
    tool_path = result.stdout.strip()
    assert tool_path, f"{tool} resolved to empty path"
    assert Path(tool_path).exists(), f"{tool} path does not exist: {tool_path}"


@pytest.mark.parametrize("tool", ["chezmoi", "uv", "pixi", "claude", "gemini", "codex"])
def test_tool_execution_in_login_shell(tool: str) -> None:
    """Verify that tools can actually execute and resolve versions in a login shell."""
    cmd = ["bash", "-l", "-c", f"{tool} --version"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    # Assert successful execution
    # This specifically catches the "mise ERROR No version is set for shim" issue
    assert result.returncode == 0, (
        f"{tool} failed to execute in login shell. Stderr: {result.stderr}"
    )
    assert result.stdout.strip() != ""


def test_zshenv_path_injection() -> None:
    """Verify that .zshenv correctly injects paths even for non-interactive shells."""
    # Simulate a zsh non-interactive shell
    cmd = ["zsh", "-c", "echo $PATH"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    path = result.stdout
    assert ".local/bin" in path
    assert "mise/shims" in path
