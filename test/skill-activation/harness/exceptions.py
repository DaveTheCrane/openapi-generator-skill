"""Custom exception classes for the skill test harness."""


class HarnessError(Exception):
    """Base exception for all harness errors."""


class ConfigError(HarnessError):
    """Raised when configuration is missing, invalid, or cannot be resolved."""


class SkillLoadError(HarnessError):
    """Raised when a SKILL.md file cannot be loaded or is missing required sections."""


class FixtureLoadError(HarnessError):
    """Raised when a fixture file cannot be loaded or fails schema validation."""


class CheckerError(HarnessError):
    """Raised when an LLM activation check fails after exhausting retries."""
