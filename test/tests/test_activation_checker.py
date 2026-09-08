"""Unit tests for test/harness/activation_checker.py.

All tests mock litellm.completion so no real LLM calls are made.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from harness.activation_checker import (
    SYSTEM_PROMPT,
    USER_TEMPLATE,
    check_activation,
)
from harness.exceptions import CheckerError
from harness.models import (
    ActivationResult,
    ExpectedOutcome,
    PromptCase,
    SkillDefinition,
)

# --------------------------------------------------------------------------- #
# Shared fixtures                                                               #
# --------------------------------------------------------------------------- #

SKILL = SkillDefinition(
    name="springboot-openapi-generator",
    description="Scaffold a Spring Boot microservice from an OpenAPI spec.",
    when_to_use="Use when the user wants to generate a Spring Boot REST API from an OpenAPI specification.",
    raw_content="---\ndescription: Scaffold a Spring Boot microservice from an OpenAPI spec.\n---\n## When to Use\nUse when...",
)

ACTIVATE_CASE = PromptCase(
    id="create-rest-api",
    prompt="Create a Spring Boot microservice from this OpenAPI spec",
    expected=ExpectedOutcome.ACTIVATE,
)

NO_ACTIVATE_CASE = PromptCase(
    id="plain-java",
    prompt="How do I write a for loop in Java?",
    expected=ExpectedOutcome.NO_ACTIVATE,
)


def _mock_response(decision: str, reasoning: str = "Test reasoning.") -> MagicMock:
    """Return a mock litellm response object with the given decision."""
    content = json.dumps({"decision": decision, "reasoning": reasoning})
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# --------------------------------------------------------------------------- #
# Happy-path: correct mapping                                                   #
# --------------------------------------------------------------------------- #


class TestCheckActivationHappyPath:
    def test_activate_decision_maps_to_enum(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.actual == ActivationResult.ACTIVATE

    def test_no_activate_decision_maps_to_enum(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("no_activate")
            result = check_activation(NO_ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.actual == ActivationResult.NO_ACTIVATE

    def test_reasoning_is_extracted(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate", "This clearly matches the skill.")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.reasoning == "This clearly matches the skill."

    def test_latency_ms_is_non_negative_integer(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert isinstance(result.latency_ms, int)
        assert result.latency_ms >= 0

    def test_prompt_id_preserved(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.prompt_id == ACTIVATE_CASE.id

    def test_prompt_text_preserved(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.prompt == ACTIVATE_CASE.prompt

    def test_expected_preserved(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.expected == ExpectedOutcome.ACTIVATE


# --------------------------------------------------------------------------- #
# passed field logic                                                            #
# --------------------------------------------------------------------------- #


class TestPassedField:
    def test_passed_true_when_actual_equals_expected_activate(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.passed is True

    def test_passed_true_when_actual_equals_expected_no_activate(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("no_activate")
            result = check_activation(NO_ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.passed is True

    def test_passed_false_when_expected_activate_actual_no_activate(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("no_activate")
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.passed is False

    def test_passed_false_when_expected_no_activate_actual_activate(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            result = check_activation(NO_ACTIVATE_CASE, SKILL, "test-model", 30)
        assert result.passed is False


# --------------------------------------------------------------------------- #
# LLM prompt content — skill and prompt fields must appear                      #
# --------------------------------------------------------------------------- #


class TestLLMPromptContent:
    def _capture_call(self, case: PromptCase, skill: SkillDefinition) -> dict:
        """Run check_activation and return the kwargs passed to litellm.completion."""
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(case, skill, "test-model", 30)
            _, kwargs = mock_llm.call_args
            # call_args may be positional; normalise
            call_args = mock_llm.call_args
            return call_args

    def test_system_prompt_sent(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        messages = mock_llm.call_args[1]["messages"]
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 1
        assert system_msgs[0]["content"] == SYSTEM_PROMPT

    def test_skill_name_in_user_message(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        messages = mock_llm.call_args[1]["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert SKILL.name in user_content

    def test_skill_description_in_user_message(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        messages = mock_llm.call_args[1]["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert SKILL.description in user_content

    def test_skill_when_to_use_in_user_message(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        messages = mock_llm.call_args[1]["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert SKILL.when_to_use in user_content

    def test_prompt_text_in_user_message(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        messages = mock_llm.call_args[1]["messages"]
        user_content = next(m["content"] for m in messages if m["role"] == "user")
        assert ACTIVATE_CASE.prompt in user_content

    def test_model_passed_to_litellm(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "my-custom-model", 30)
        assert mock_llm.call_args[1]["model"] == "my-custom-model"

    def test_timeout_passed_to_litellm(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 45)
        assert mock_llm.call_args[1]["timeout"] == 45


# --------------------------------------------------------------------------- #
# Retry logic — malformed / missing-field JSON                                  #
# --------------------------------------------------------------------------- #


class TestRetryBehaviour:
    def _make_bad_response(self, content: str) -> MagicMock:
        message = MagicMock()
        message.content = content
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        return response

    def test_retries_once_on_invalid_json_then_succeeds(self):
        bad = self._make_bad_response("not json at all")
        good = _mock_response("activate", "Retry succeeded.")
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = [bad, good]
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert mock_llm.call_count == 2
        assert result.actual == ActivationResult.ACTIVATE
        assert result.reasoning == "Retry succeeded."

    def test_retries_once_on_missing_decision_then_succeeds(self):
        bad = self._make_bad_response(json.dumps({"reasoning": "No decision field"}))
        good = _mock_response("no_activate")
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = [bad, good]
            result = check_activation(NO_ACTIVATE_CASE, SKILL, "test-model", 30)
        assert mock_llm.call_count == 2
        assert result.actual == ActivationResult.NO_ACTIVATE

    def test_retries_once_on_missing_reasoning_then_succeeds(self):
        bad = self._make_bad_response(json.dumps({"decision": "activate"}))
        good = _mock_response("activate", "Now with reasoning.")
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = [bad, good]
            result = check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert mock_llm.call_count == 2
        assert result.reasoning == "Now with reasoning."

    def test_raises_checker_error_after_two_bad_responses(self):
        bad = self._make_bad_response("still not json")
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = [bad, bad]
            with pytest.raises(CheckerError, match="unparseable response"):
                check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert mock_llm.call_count == 2

    def test_raises_checker_error_after_bad_then_missing_field(self):
        bad1 = self._make_bad_response("not json")
        bad2 = self._make_bad_response(json.dumps({"only": "wrong fields"}))
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = [bad1, bad2]
            with pytest.raises(CheckerError):
                check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)

    def test_no_retry_on_first_success(self):
        """When the first call succeeds, litellm should be called exactly once."""
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.return_value = _mock_response("activate")
            check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
        assert mock_llm.call_count == 1


# --------------------------------------------------------------------------- #
# API / network exceptions → CheckerError                                       #
# --------------------------------------------------------------------------- #


class TestAPIExceptions:
    def test_api_exception_raises_checker_error(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = Exception("Connection refused")
            with pytest.raises(CheckerError, match="LLM API call failed"):
                check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)

    def test_timeout_exception_raises_checker_error(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = TimeoutError("Request timed out")
            with pytest.raises(CheckerError):
                check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)

    def test_checker_error_includes_original_message(self):
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = RuntimeError("auth failed: 401")
            with pytest.raises(CheckerError, match="auth failed"):
                check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)

    def test_api_exception_on_retry_raises_checker_error(self):
        """First call returns bad JSON, retry raises an API exception."""
        bad = MagicMock()
        bad.choices = [MagicMock()]
        bad.choices[0].message.content = "not json"
        with patch("harness.activation_checker.litellm.completion") as mock_llm:
            mock_llm.side_effect = [bad, Exception("rate limited")]
            with pytest.raises(CheckerError):
                check_activation(ACTIVATE_CASE, SKILL, "test-model", 30)
