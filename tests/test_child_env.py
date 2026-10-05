# Copyright (c) 2026 Raymond Manaloto
"""Tests for the child-process environment scrub."""

from __future__ import annotations

import os

import pytest
from dotfiles_setup.child_env import (
    ENV_DIFF_NAME,
    GIT_CONTEXT_NAMES,
    clean_env,
    dropped_names,
    is_credential,
    without_color_forcing,
    without_env_diff,
    without_git_context,
)

# Values are named rather than inline so no assertion below reads as a
# hardcoded credential (ruff S105) — and so a value change stays in one place.
SENTINEL = "s3nt1nel"
PLAIN = "kept"

SAMPLE = {
    ENV_DIFF_NAME: "eJxopaque",
    "AWS_SECRET_ACCESS_KEY": SENTINEL,
    "AWS_ACCESS_KEY_ID": SENTINEL,
    "GITHUB_TOKEN": SENTINEL,
    "BSKY_APP_PASSWORD": SENTINEL,
    "GOOGLE_CLIENT_SECRET": SENTINEL,
    "PATH": "/usr/bin",
    "HOME": "/home/x",
    "AWS_REGION": "us-east-1",
    "TOKENIZER_BACKEND": "hf",
}


@pytest.mark.parametrize("use_ambient", [False, True])
def test_without_color_forcing_drops_only_forcing_names(
    monkeypatch: pytest.MonkeyPatch, *, use_ambient: bool
) -> None:
    """FAIL arm: retaining CLICOLOR_FORCE colours gh even with NO_COLOR=1."""
    source = {
        **SAMPLE,
        "FORCE_COLOR": "3",
        "CLICOLOR_FORCE": "1",
        "GH_FORCE_TTY": "1",
        "PYTHON_COLORS": "1",
    }
    before = dict(source)
    # The explicit-base arm points os.environ elsewhere, so ignoring `base` fails.
    monkeypatch.setattr(os, "environ", source if use_ambient else {"PATH": "/x"})

    out = without_color_forcing(None if use_ambient else source)

    assert out == {**SAMPLE, "NO_COLOR": "1"}
    assert source == before
    assert out is not source


@pytest.mark.parametrize("no_color", ["", "0"])
def test_without_color_forcing_overwrites_no_color(no_color: str) -> None:
    source = {"NO_COLOR": no_color, "PATH": "/sentinel/bin"}

    assert without_color_forcing(source) == {
        "NO_COLOR": "1",
        "PATH": "/sentinel/bin",
    }
    assert source["NO_COLOR"] == no_color


def test_without_color_forcing_keeps_explicit_empty_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FAIL arm: treating an empty base as absent imports ambient names."""
    monkeypatch.setattr(os, "environ", {"PATH": "/sentinel/bin"})

    assert without_color_forcing({}) == {"NO_COLOR": "1"}


def test_without_env_diff_drops_only_the_blob() -> None:
    """The default strength must not break a child by removing what it needs."""
    out = without_env_diff(SAMPLE)
    assert ENV_DIFF_NAME not in out
    assert out["AWS_SECRET_ACCESS_KEY"] == SENTINEL
    assert len(out) == len(SAMPLE) - 1


def test_clean_env_drops_every_credential_shaped_name() -> None:
    out = clean_env(SAMPLE)
    for name in (
        ENV_DIFF_NAME,
        "AWS_SECRET_ACCESS_KEY",
        "AWS_ACCESS_KEY_ID",
        "GITHUB_TOKEN",
        "BSKY_APP_PASSWORD",
        "GOOGLE_CLIENT_SECRET",
    ):
        assert name not in out, name


def test_clean_env_keeps_the_ordinary_environment() -> None:
    """The control arm: a scrub that removed everything would also 'pass' above."""
    out = clean_env(SAMPLE)
    assert out["PATH"] == "/usr/bin"
    assert out["HOME"] == "/home/x"
    assert out["AWS_REGION"] == "us-east-1"


def test_a_name_that_merely_starts_with_token_is_not_a_credential() -> None:
    """`TOKENIZER_BACKEND` contains 'TOKEN' but is not one — anchor on segments."""
    assert not is_credential("TOKENIZER_BACKEND")
    assert clean_env(SAMPLE)["TOKENIZER_BACKEND"] == "hf"


def test_keep_is_an_explicit_per_call_exception() -> None:
    out = clean_env(SAMPLE, keep=frozenset({"GITHUB_TOKEN"}))
    assert out["GITHUB_TOKEN"] == SENTINEL
    assert "AWS_SECRET_ACCESS_KEY" not in out


def test_the_source_environment_is_never_modified() -> None:
    before = dict(SAMPLE)
    clean_env(SAMPLE)
    without_env_diff(SAMPLE)
    without_git_context(SAMPLE)
    assert before == SAMPLE


def test_without_git_context_drops_mise_blob_and_repository_routing() -> None:
    source = {
        **SAMPLE,
        "GIT_DIR": "/workspace/outer/.git",
        "GIT_WORK_TREE": "/workspace/outer",
        "GIT_INDEX_FILE": "/workspace/outer/.git/index",
        "GIT_COMMON_DIR": "/workspace/outer/.git",
        "GIT_OBJECT_DIRECTORY": "/workspace/outer/.git/objects",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES": "/workspace/outer/.git/objects",
    }

    out = without_git_context(source)

    assert ENV_DIFF_NAME not in out
    assert not GIT_CONTEXT_NAMES & out.keys()
    assert out["PATH"] == "/usr/bin"
    assert out["GITHUB_TOKEN"] == SENTINEL


def test_dropped_names_reports_names_and_never_values() -> None:
    names = dropped_names(SAMPLE)
    assert ENV_DIFF_NAME in names
    assert "GITHUB_TOKEN" in names
    assert "PATH" not in names
    assert all(SAMPLE[n] not in "".join(names) for n in names if SAMPLE[n])
