"""Core data models for the skill test harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ExpectedOutcome(Enum):
    """The expected activation outcome for a prompt case."""

    ACTIVATE = "activate"
    NO_ACTIVATE = "no_activate"


class ActivationResult(Enum):
    """The actual activation decision returned by the LLM judge."""

    ACTIVATE = "activate"
    NO_ACTIVATE = "no_activate"


@dataclass
class HarnessConfig:
    """Resolved runtime configuration for a harness run."""

    skill_path: str
    fixture_path: str
    model: str = "claude-3-5-haiku-20241022"
    timeout_seconds: int = 30
    verbose: bool = False
    api_base: str | None = None
    extra_params: dict = field(default_factory=dict)


@dataclass
class SkillDefinition:
    """Parsed representation of a SKILL.md file."""

    name: str
    description: str
    when_to_use: str        # Full text of the "## When to Use" section
    raw_content: str        # Full markdown content verbatim


@dataclass
class PromptCase:
    """A single test case from a fixture file."""

    id: str
    prompt: str
    expected: ExpectedOutcome
    notes: str | None = None


@dataclass
class CheckResult:
    """The outcome of a single activation check."""

    prompt_id: str
    prompt: str
    expected: ExpectedOutcome
    actual: ActivationResult | None     # None if an error occurred
    passed: bool
    reasoning: str
    latency_ms: int
    error: str | None = None            # Set if an exception was caught


@dataclass
class RunSummary:
    """Aggregated result of all activation checks in a single run."""

    total: int
    passed: int
    failed: int
    errors: int
    results: list[CheckResult] = field(default_factory=list)
    duration_ms: int = 0
