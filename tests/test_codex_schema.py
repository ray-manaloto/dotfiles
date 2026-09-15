# Copyright (c) 2026 Raymond Manaloto
"""Tests for codex_schema module."""

from __future__ import annotations

import json
import subprocess
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from dotfiles_setup import codex_schema

if TYPE_CHECKING:
    from pathlib import Path
import pathlib
from types import SimpleNamespace


class TestSchemaPath:
    """Test schema_path resolution."""

    def test_schema_path_resolves_correctly(self, tmp_path: Path) -> None:
        """Schema path should resolve correctly."""
        result = codex_schema.schema_path(tmp_path)
        expected = tmp_path / "schemas" / "codex_app_server_protocol.schemas.json"
        assert result == expected


class TestValidateSchemaExists:
    """Test schema existence check."""

    def test_validate_schema_exists_returns_false_when_missing(
        self, tmp_path: Path
    ) -> None:
        """Should return False when schema file does not exist."""
        assert not codex_schema.validate_schema_exists(tmp_path)

    def test_validate_schema_exists_returns_true_when_present(
        self, tmp_path: Path
    ) -> None:
        """Should return True when schema file exists."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        schema_file = schema_dir / "codex_app_server_protocol.schemas.json"
        schema_file.write_text("{}")

        assert codex_schema.validate_schema_exists(tmp_path)


class TestLoadSchema:
    """Test schema loading."""

    def test_load_schema_returns_none_when_missing(self, tmp_path: Path) -> None:
        """Should return None when schema file does not exist."""
        assert codex_schema.load_schema(tmp_path) is None

    def test_load_schema_returns_dict_when_present(self, tmp_path: Path) -> None:
        """Should parse and return schema as dict."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        schema_file = schema_dir / "codex_app_server_protocol.schemas.json"
        test_schema = {"version": "0.154.0", "properties": {}}
        schema_file.write_text(json.dumps(test_schema))

        loaded = codex_schema.load_schema(tmp_path)
        assert loaded == test_schema
        assert loaded is not None
        assert loaded["version"] == "0.154.0"


class TestCheckSchemaCurrency:
    """Test schema currency validation."""

    def test_check_schema_currency_returns_false_when_missing(
        self, tmp_path: Path
    ) -> None:
        """Should return False when schema does not exist."""
        is_current, msg = codex_schema.check_schema_currency(tmp_path, "0.154.0")
        assert not is_current
        assert "not found" in msg.lower()

    def test_check_schema_currency_returns_true_when_present(
        self, tmp_path: Path
    ) -> None:
        """Should return True when schema file exists and is valid JSON."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        schema_file = schema_dir / "codex_app_server_protocol.schemas.json"
        test_schema = {"version": "0.154.0"}
        schema_file.write_text(json.dumps(test_schema))

        is_current, msg = codex_schema.check_schema_currency(tmp_path, "0.154.0")
        assert is_current
        assert "0.154.0" in msg

    def test_check_schema_currency_returns_false_for_invalid_json(
        self, tmp_path: Path
    ) -> None:
        """Should return False when schema contains invalid JSON."""
        schema_dir = tmp_path / "schemas"
        schema_dir.mkdir()
        schema_file = schema_dir / "codex_app_server_protocol.schemas.json"
        schema_file.write_text("{ invalid json")

        with pytest.raises(json.JSONDecodeError):
            codex_schema.check_schema_currency(tmp_path, "0.154.0")


class TestGenerateSchema:
    """Test schema generation."""

    def test_generate_schema_creates_output_directory(self, tmp_path: Path) -> None:
        """Should create output directory if it does not exist."""
        output_dir = tmp_path / "schemas"
        assert not output_dir.exists()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            codex_schema.generate_schema(tmp_path, output_dir)

            assert output_dir.exists()

    def test_generate_schema_returns_true_only_when_the_bundle_lands(
        self, tmp_path: Path
    ) -> None:
        """rc=0 is not success — the bundle must actually arrive in output_dir.

        The generator writes to a staging dir and only the bundle is copied out.
        A subprocess that exits 0 while producing no bundle is a FAILURE, and
        returning True there would leave doctor asserting against a file that
        was never written. Both arms are checked here, which is the point: the
        happy arm alone would pass even if the copy step were deleted.
        """
        output_dir = tmp_path / "schemas"
        bundle = "codex_app_server_protocol.schemas.json"

        def _writes_the_bundle(
            cmd: list[str], *_a: object, **_k: object
        ) -> SimpleNamespace:
            staging = pathlib.Path(cmd[cmd.index("--out") + 1])
            staging.mkdir(parents=True, exist_ok=True)
            (staging / bundle).write_text('{"generated": true}')
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with patch("subprocess.run", side_effect=_writes_the_bundle):
            assert codex_schema.generate_schema(tmp_path, output_dir) is True
        assert (output_dir / bundle).is_file(), "the bundle must be copied out"
        assert not list(output_dir.glob("*Params.json")), (
            "only bundles may be copied — per-message schemas stay in staging"
        )

        # FAIL ARM: rc=0 but the generator produced nothing.
        empty_out = tmp_path / "schemas_empty"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            assert codex_schema.generate_schema(tmp_path, empty_out) is False, (
                "rc=0 with no bundle produced must NOT report success"
            )

    def test_generate_schema_returns_false_on_failure(self, tmp_path: Path) -> None:
        """Should return False when codex app-server command fails."""
        output_dir = tmp_path / "schemas"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            result = codex_schema.generate_schema(tmp_path, output_dir)

            assert result is False

    def test_generate_schema_calls_correct_command(self, tmp_path: Path) -> None:
        """Should invoke correct codex command."""
        output_dir = tmp_path / "schemas"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            codex_schema.generate_schema(tmp_path, output_dir)

            # Verify the command was called correctly
            call_args = mock_run.call_args[0][0]
            assert "mise" in call_args
            assert "codex" in call_args
            assert "app-server" in call_args
            assert "generate-json-schema" in call_args

            # `--out` must NOT be the curated schemas/ directory. The generator
            # emits the whole protocol surface — measured 305 files, including
            # per-message schemas and v1/v2 subtrees — and only the bundle is
            # kept. Pointing it straight at schemas/ is what dumped 303
            # redundant files into a reviewed vendoring directory.
            out_target = call_args[call_args.index("--out") + 1]
            assert out_target != str(output_dir), (
                "generation must stage in a temp dir, not write schemas/ directly"
            )
            assert "codex-schema-" in out_target, (
                f"expected a codex-schema-* staging dir, got {out_target!r}"
            )


class TestGetInstalledCodexVersion:
    """Test codex version detection."""

    def test_get_installed_codex_version_parses_correctly(self) -> None:
        """Should parse version from 'codex-cli X.Y.Z' output."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "codex-cli 0.154.0\n"
            mock_run.return_value.returncode = 0
            version = codex_schema.get_installed_codex_version()

            assert version == "0.154.0"

    def test_get_installed_codex_version_raises_on_failure(self) -> None:
        """Should raise CalledProcessError when codex command fails."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "codex")
            with pytest.raises(subprocess.CalledProcessError):
                codex_schema.get_installed_codex_version()
