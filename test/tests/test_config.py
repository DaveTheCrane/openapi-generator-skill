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
# load_config — api_base
# ---------------------------------------------------------------------------


class TestLoadConfigApiBase:
    def test_default_api_base_is_none(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_API_BASE", raising=False)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.api_base is None

    def test_file_provides_api_base(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_API_BASE", raising=False)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\napi_base: http://localhost:11434\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.api_base == "http://localhost:11434"

    def test_env_var_overrides_file_api_base(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\napi_base: http://file-host:11434\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SKILL_HARNESS_API_BASE", "http://env-host:11434")
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.api_base == "http://env-host:11434"

    def test_cli_api_base_overrides_env_var(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.setenv("SKILL_HARNESS_API_BASE", "http://env-host:11434")
        cfg = load_config(
            argv=[
                "--skill", str(skill),
                "--fixture", str(fixture),
                "--api-base", "http://cli-host:11434",
            ],
            cwd=str(tmp_path),
        )
        assert cfg.api_base == "http://cli-host:11434"

    def test_cli_api_base_overrides_file(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_API_BASE", raising=False)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\napi_base: http://file-host:11434\n",
            encoding="utf-8",
        )
        cfg = load_config(
            argv=["--api-base", "http://cli-host:11434"],
            cwd=str(tmp_path),
        )
        assert cfg.api_base == "http://cli-host:11434"


# ---------------------------------------------------------------------------
# load_config — extra_params
# ---------------------------------------------------------------------------


class TestLoadConfigExtraParams:
    def test_default_extra_params_is_empty_dict(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.extra_params == {}

    def test_file_provides_extra_params(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\n"
            "extra_params:\n  think: false\n  num_predict: 300\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.extra_params == {"think": False, "num_predict": 300}

    def test_non_mapping_extra_params_raises(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nextra_params:\n  - not\n  - a\n  - map\n",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="extra_params"):
            load_config(argv=[], cwd=str(tmp_path))


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


# ---------------------------------------------------------------------------
# load_config — report_format / report_file
# ---------------------------------------------------------------------------


class TestLoadConfigReport:
    def test_default_report_format_is_text(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_REPORT_FORMAT", raising=False)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.report_format == "text"

    def test_default_report_file_is_none(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_REPORT_FILE", raising=False)
        cfg = load_config(
            argv=["--skill", str(skill), "--fixture", str(fixture)],
            cwd=str(tmp_path),
        )
        assert cfg.report_file is None

    def test_cli_report_format(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        cfg = load_config(
            argv=[
                "--skill", str(skill),
                "--fixture", str(fixture),
                "--report-format", "json",
            ],
            cwd=str(tmp_path),
        )
        assert cfg.report_format == "json"

    def test_cli_report_file(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        out = tmp_path / "out.json"
        cfg = load_config(
            argv=[
                "--skill", str(skill),
                "--fixture", str(fixture),
                "--report-file", str(out),
            ],
            cwd=str(tmp_path),
        )
        assert cfg.report_file == str(out)

    def test_file_provides_report_format(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_REPORT_FORMAT", raising=False)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nreport_format: junit\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.report_format == "junit"

    def test_file_provides_report_file(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_REPORT_FILE", raising=False)
        out = tmp_path / "file-report.xml"
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nreport_file: {out}\n",
            encoding="utf-8",
        )
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.report_file == str(out)

    def test_env_overrides_file_report_format(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nreport_format: text\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SKILL_HARNESS_REPORT_FORMAT", "json")
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.report_format == "json"

    def test_env_overrides_file_report_file(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        file_path = tmp_path / "from-file.json"
        env_path = tmp_path / "from-env.json"
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nreport_file: {file_path}\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("SKILL_HARNESS_REPORT_FILE", str(env_path))
        cfg = load_config(argv=[], cwd=str(tmp_path))
        assert cfg.report_file == str(env_path)

    def test_cli_overrides_env_report_format(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.setenv("SKILL_HARNESS_REPORT_FORMAT", "json")
        cfg = load_config(
            argv=[
                "--skill", str(skill),
                "--fixture", str(fixture),
                "--report-format", "junit",
            ],
            cwd=str(tmp_path),
        )
        assert cfg.report_format == "junit"

    def test_cli_overrides_env_report_file(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        env_path = tmp_path / "env.json"
        cli_path = tmp_path / "cli.json"
        monkeypatch.setenv("SKILL_HARNESS_REPORT_FILE", str(env_path))
        cfg = load_config(
            argv=[
                "--skill", str(skill),
                "--fixture", str(fixture),
                "--report-file", str(cli_path),
            ],
            cwd=str(tmp_path),
        )
        assert cfg.report_file == str(cli_path)

    def test_invalid_report_format_from_file_raises(self, tmp_path, monkeypatch):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        monkeypatch.delenv("SKILL_HARNESS_REPORT_FORMAT", raising=False)
        (tmp_path / "harness.yaml").write_text(
            f"skill: {skill}\nfixture: {fixture}\nreport_format: xml\n",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="report_format"):
            load_config(argv=[], cwd=str(tmp_path))

    def test_nonexistent_report_file_parent_raises(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        missing = tmp_path / "no_such_dir" / "report.json"
        with pytest.raises(ConfigError, match="report_file"):
            load_config(
                argv=[
                    "--skill", str(skill),
                    "--fixture", str(fixture),
                    "--report-file", str(missing),
                ],
                cwd=str(tmp_path),
            )

    def test_existing_parent_report_file_ok(self, tmp_path):
        skill = _make_skill(tmp_path)
        fixture = _make_fixture(tmp_path)
        # File does not pre-exist but parent (tmp_path) does.
        out = tmp_path / "will-be-created.json"
        cfg = load_config(
            argv=[
                "--skill", str(skill),
                "--fixture", str(fixture),
                "--report-file", str(out),
            ],
            cwd=str(tmp_path),
        )
        assert cfg.report_file == str(out)
        assert not out.exists()
