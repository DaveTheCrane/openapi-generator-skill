"""Activation checker — calls an LLM judge to decide whether a skill activates."""

from __future__ import annotations

import json
import time

import litellm

from harness.exceptions import CheckerError
from harness.models import (
    ActivationResult,
    CheckResult,
    ExpectedOutcome,
    PromptCase,
    SkillDefinition,
)

# --------------------------------------------------------------------------- #
# Prompt templates (verbatim from the design document)                          #
# --------------------------------------------------------------------------- #

SYSTEM_PROMPT = """You are an AI agent skill router. Your job is to decide whether a given user prompt should activate a specific agent skill.

You will be given:
1. A skill definition (name, description, and "when to use" guidance)
2. A user prompt

Respond with a JSON object with exactly two fields:
- "decision": either "activate" or "no_activate"
- "reasoning": a brief explanation (1-2 sentences)

Do not include any other text outside the JSON object."""

USER_TEMPLATE = """## Skill Definition

**Name**: {name}

**Description**: {description}

**When to Use**:
{when_to_use}

## User Prompt

{prompt}

Should this skill activate for the above prompt?"""

# --------------------------------------------------------------------------- #
# Internal helpers                                                              #
# --------------------------------------------------------------------------- #

_VALID_DECISIONS = {"activate", "no_activate"}


def _parse_response(content: str) -> tuple[str, str]:
    """Parse the LLM response content and return (decision, reasoning).

    Raises ``ValueError`` if the JSON is malformed or required fields are absent
    or the decision value is not recognised.
    """
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Response is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object, got {type(data).__name__}")

    if "decision" not in data:
        raise ValueError("JSON response is missing the 'decision' field")
    if "reasoning" not in data:
        raise ValueError("JSON response is missing the 'reasoning' field")

    decision = data["decision"]
    if decision not in _VALID_DECISIONS:
        raise ValueError(
            f"Unknown decision value {decision!r}; expected one of {_VALID_DECISIONS}"
        )

    return decision, str(data["reasoning"])


def _call_llm(
    messages: list[dict],
    model: str,
    timeout_seconds: int,
    api_base: str | None = None,
    extra_params: dict | None = None,
) -> str:
    """Call litellm and return the response message content string.

    ``api_base`` is forwarded only when provided. ``extra_params`` is spread
    into the call to support provider-specific options (e.g. ``think``,
    ``num_predict`` for Ollama).

    Raises ``CheckerError`` on any litellm / network exception.
    """
    kwargs: dict = {
        "model": model,
        "messages": messages,
        "timeout": timeout_seconds,
    }
    if api_base is not None:
        kwargs["api_base"] = api_base
    if extra_params:
        kwargs.update(extra_params)

    try:
        response = litellm.completion(**kwargs)
        return response.choices[0].message.content  # type: ignore[union-attr]
    except Exception as exc:
        raise CheckerError(f"LLM API call failed: {exc}") from exc


# --------------------------------------------------------------------------- #
# Public API                                                                    #
# --------------------------------------------------------------------------- #


def check_activation(
    prompt_case: PromptCase,
    skill: SkillDefinition,
    model: str,
    timeout_seconds: int,
    api_base: str | None = None,
    extra_params: dict | None = None,
) -> CheckResult:
    """Determine whether *prompt_case* should activate *skill* via an LLM judge.

    API keys are read exclusively from environment variables (e.g.
    ``ANTHROPIC_API_KEY``, ``OPENAI_API_KEY``) as consumed by ``litellm``.

    Returns a :class:`~harness.models.CheckResult` describing the outcome.

    Raises :class:`~harness.exceptions.CheckerError` if the LLM call fails or
    the response cannot be parsed after one retry.
    """
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": USER_TEMPLATE.format(
                name=skill.name,
                description=skill.description,
                when_to_use=skill.when_to_use,
                prompt=prompt_case.prompt,
            ),
        },
    ]

    start = time.perf_counter()

    # First attempt
    content = _call_llm(messages, model, timeout_seconds, api_base, extra_params)

    try:
        decision, reasoning = _parse_response(content)
    except ValueError:
        # Retry once on malformed / missing-field response
        content = _call_llm(messages, model, timeout_seconds, api_base, extra_params)
        try:
            decision, reasoning = _parse_response(content)
        except ValueError as exc:
            raise CheckerError(
                f"LLM returned unparseable response after retry: {exc}"
            ) from exc

    latency_ms = int((time.perf_counter() - start) * 1000)

    actual = ActivationResult(decision)
    passed = actual == ActivationResult(prompt_case.expected.value)

    return CheckResult(
        prompt_id=prompt_case.id,
        prompt=prompt_case.prompt,
        expected=prompt_case.expected,
        actual=actual,
        passed=passed,
        reasoning=reasoning,
        latency_ms=latency_ms,
    )
