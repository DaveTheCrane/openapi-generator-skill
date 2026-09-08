"""Unit tests for test/harness/config.py — load_config() and helpers."""

from __future__ import annotations

import os
import textwrap
from pathlib import Path

import pytest

from harness.config import load_config, validate_timeout
from harness.exceptions import ConfigError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_skill(tmp_path: Path, name: str = "skill.md") -> Path:
    """Create a minimal readable SKILL.md file and return its path."""
    p = tmp_path / name
    p.write_text("# Skill\n", encoding="utf-8")
    return p


def _make_fixture(tmp_path: Path, name: str = "fixture.yaml") -> Path:
    """Create a minimal readable fixture file and return its path."""
    p = tmp_path / name
    p.write_text("cases: []\n", encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# validate_timeout
# ---------------------------------------------------------------------------


class TestValidateTimeout:
    def test_accepts_lower_bound(self):
        validate_timeout(1)  # should not raise

    def test_accepts_upper_bound(self):
        validate_timeout(300)  # should not raise

    def test_accepts_mid_range(self):
        validate_timeout(30)  # should not raise

    def test_rejects_zero(self):
        with pytest.raises(ConfigError):
            validate_timeout(0)

    def test_rejects_negative(self):
        with pytest.raises(ConfigError):
            validate_timeout(-1)

    def test_rejects_above_300(self):
        with pytest.raises(ConfigError):
            validate_timeout(301)


# ---------------------------------------------------------------------------
# load_config — defaults
# ---------------------------------------------------------------------------


class TestLoadConfigDefaults:
    def test_defaults_model(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.model == "claude-3-5-haiku-20241022"

    def test_defaults_timeout(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.timeout_seconds == 30

    def test_defaults_verbose_false(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.verbose is False


# ---------------------------------------------------------------------------
# load_config — CLI arguments
# ---------------------------------------------------------------------------


class TestLoadConfigCLI:
    def test_cli_skill_and_fixture(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.skill_path == str(skill)
        assert cfg.fixture_path == str(fixture)

    def test_cli_model(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture), "--model", "gpt-4o"],
            cwd=str(tmp_path),
        )
        assert cfg.model == "gpt-4o"

    def test_cli_timeout(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture), "--timeout", "60"],
            cwd=str(tmp_path),
        )
        assert cfg.timeout_seconds == 60

    def test_cli_verbose(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture), "--verbose"],
            cwd=str(tmp_path),
        )
        assert cfg.verbose is True


# ---------------------------------------------------------------------------
# load_config — harness.yaml config file
# ---------------------------------------------------------------------------


class TestLoadConfigFileDefaults:
    def test_file_provides_model(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nmodel: my-file-model\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.model == "my-file-model"

    def test_file_provides_timeout(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\ntimeout: 120\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.timeout_seconds == 120

    def test_file_provides_verbose(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nverbose: true\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.verbose is True


# ---------------------------------------------------------------------------
# load_config — precedence: CLI overrides file
# ---------------------------------------------------------------------------


class TestLoadConfigPrecedence:
    def test_cli_model_overrides_file(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nmodel: file-model\n",
            encoding="utf-8",
        )
        cfg = load_config(
            argv=["--model", "cli-model"],
            cwd=str(tmp_path),
        )
        assert cfg.model == "cli-model"

    def test_cli_timeout_overrides_file(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\ntimeout: 200\n",
            encoding="utf-8",
        )
        cfg = load_config(
            argv=["--timeout", "5"],
            cwd=str(tmp_path),
        )
        assert cfg.timeout_seconds == 5

    def test_cli_skill_overrides_file(self, tmp_path):
        file_skill = _make_skill(tmp_path, "file_skill.md")
        cli_skill = _make_skill(tmp_path, "cli_skill.md")
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {file_skill}\nfixture: {fixture}\n",
            encoding="utf-8",
        )
        cfg = load_config(
            argv=["--skill", str(cli_skill)],
            cwd=str(tmp_path),
        )
        assert cfg.skill_path == str(cli_skill)


# ---------------------------------------------------------------------------
# load_config — precedence: env var overrides file, CLI overrides env var
# ---------------------------------------------------------------------------


class TestLoadConfigEnvVar:
    def test_env_var_overrides_file(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nmodel: file-model\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SKILL_HARNESS_MODEL", "env-model")
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.model == "env-model"

    def test_cli_model_overrides_env_var(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.setenv("SKILL_HARNESS_MODEL", "env-model")
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture), "--model", "cli-model"],
            cwd=str(tmp_path),
        )
        assert cfg.model == "cli-model"

    def test_no_env_var_uses_default(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_MODEL", raising=False)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.model == "claude-3-5-haiku-20241022"


# ---------------------------------------------------------------------------
# load_config — validation errors
# ---------------------------------------------------------------------------


class TestLoadConfigValidationErrors:
    def test_missing_skill_raises(self, tmp_path):
        fixture = _make_fixture(tmp_path)
        with pytest.raises(ConfigError, match="skill"):
            load_config(
                argv=["--fixture", str(fixture)],
                cwd=str(tmp_path),
            )

    def test_missing_fixture_raises(self, tmp_path):
        skill = _make_skill(tmp_path)
        with pytest.raises(ConfigError, match="fixture"):
            load_config(
                argv=["--skill", str(skill)],
                cwd=str(tmp_path),
            )

    def test_nonexistent_skill_path_raises(self, tmp_path):
        fixture = _make_fixture(tmp_path)
        with pytest.raises(ConfigError, match="skill"):
            load_config(
                argv=["--skill", "/nonexistent/path/skill.md", "--fixture", str(fixture)],
                cwd=str(tmp_path),
            )

    def test_nonexistent_fixture_path_raises(self, tmp_path):
        skill = _make_skill(tmp_path)
        with pytest.raises(ConfigError, match="fixture"):
            load_config(
                argv=["--skill", str(skill), "--fixture", "/nonexistent/fixture.yaml"],
                cwd=str(tmp_path),
            )

    def test_timeout_zero_raises(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        with pytest.raises(ConfigError):
            load_config(
                argv=["--skill", str(skill), "--fixture", str(fixture), "--timeout", "0"],
                cwd=str(tmp_path),
            )

    def test_timeout_301_raises(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        with pytest.raises(ConfigError):
            load_config(
                argv=["--skill", str(skill), "--fixture", str(fixture), "--timeout", "301"],
                cwd=str(tmp_path),
            )
