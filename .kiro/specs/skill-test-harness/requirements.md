# Requirements Document

## Introduction

This document specifies the requirements for a Python test harness that validates agent skill activation logic. The harness accepts a skill definition file (SKILL.md) and a YAML fixture file containing labeled prompts, runs each prompt through an LLM-based activation checker, and reports pass/fail results with a structured exit code. The harness is skill-agnostic and works with any skill that follows the standard SKILL.md format.

## Glossary

- **Harness**: The skill test harness — the Python application described by these requirements.
- **Skill**: An agent skill defined by a SKILL.md file containing a YAML front-matter `description` and a `## When to Use` section.
- **Fixture**: A YAML file containing a list of prompt cases, each with an ID, a prompt, and an expected activation outcome.
- **Prompt Case**: A single test case entry in a fixture file, comprising an ID, a user prompt, and an expected outcome.
- **Activation Check**: The process of determining whether a given prompt would cause a skill to activate.
- **LLM Judge**: An LLM called via `litellm` that evaluates whether a prompt matches a skill's intent.
- **CheckResult**: The outcome of a single activation check, including the actual decision, whether it matched the expected outcome, LLM reasoning, and latency.
- **RunSummary**: The aggregated result of all activation checks in a single run.
- **Config**: The resolved runtime configuration for a harness run, sourced from CLI args, environment variables, and an optional `harness.yaml` file.

---

## Requirements

### Requirement 1: Configuration Loading

**User Story:** As a developer, I want to configure the harness via CLI arguments and environment variables, so that I can point it at any skill and fixture without modifying source code.

#### Acceptance Criteria

1. THE Harness SHALL accept a `--skill` CLI argument specifying the path to a SKILL.md file.
2. THE Harness SHALL accept a `--fixture` CLI argument specifying the path to a YAML fixture file.
3. THE Harness SHALL accept a `--model` CLI argument specifying the LLM model identifier to use.
4. THE Harness SHALL accept a `--timeout` CLI argument specifying the per-prompt LLM call timeout in seconds.
5. THE Harness SHALL accept a `--verbose` CLI flag that enables per-prompt reasoning output.
6. WHEN `--model` is not provided via CLI, THE Harness SHALL use the value of the `SKILL_HARNESS_MODEL` environment variable if set.
7. WHEN neither `--model` nor `SKILL_HARNESS_MODEL` is set, THE Harness SHALL default to `claude-3-5-haiku-20241022`.
8. WHEN a `harness.yaml` file exists in the current working directory, THE Harness SHALL load configuration defaults from it, with CLI arguments taking precedence over file values.
9. IF the resolved `skill_path` does not point to an existing readable file, THEN THE Harness SHALL print a descriptive error to stderr and exit with code 2.
10. IF the resolved `fixture_path` does not point to an existing readable file, THEN THE Harness SHALL print a descriptive error to stderr and exit with code 2.
11. THE Harness SHALL validate that `timeout_seconds` is an integer between 1 and 300 inclusive; IF it is not, THEN THE Harness SHALL print a descriptive error to stderr and exit with code 2.

---

### Requirement 2: Skill Loading

**User Story:** As a developer, I want the harness to parse any standard SKILL.md file, so that I can test skills without writing custom adapters.

#### Acceptance Criteria

1. THE Skill_Loader SHALL read the SKILL.md file at the configured path and return a `SkillDefinition`.
2. THE Skill_Loader SHALL extract the `description` field from the YAML front matter of the SKILL.md file.
3. THE Skill_Loader SHALL extract the full text body of the `## When to Use` section from the SKILL.md file.
4. IF the SKILL.md file is missing a `description` field in its front matter, THEN THE Skill_Loader SHALL raise a `SkillLoadError` with a descriptive message.
5. IF the SKILL.md file is missing a `## When to Use` section, THEN THE Skill_Loader SHALL raise a `SkillLoadError` with a descriptive message.
6. THE Skill_Loader SHALL preserve the full raw content of the SKILL.md file in the returned `SkillDefinition`.

---

### Requirement 3: Fixture Loading

**User Story:** As a developer, I want to define test cases in a YAML fixture file with labeled prompts, so that I can maintain a curated test suite for each skill.

#### Acceptance Criteria

1. THE Fixture_Loader SHALL parse a YAML fixture file and return a list of `PromptCase` objects.
2. EACH Prompt_Case SHALL have a non-empty string `id` field matching the pattern `^[a-zA-Z0-9_-]+$`.
3. EACH Prompt_Case SHALL have a non-empty string `prompt` field.
4. EACH Prompt_Case SHALL have an `expected` field with a value of either `activate` or `no_activate`.
5. THE Fixture_Loader SHALL treat the `notes` field as optional; its absence SHALL NOT cause an error.
6. IF the fixture file contains duplicate `id` values, THEN THE Fixture_Loader SHALL raise a `FixtureLoadError` identifying the duplicate IDs.
7. IF any required field (`id`, `prompt`, or `expected`) is missing from a case, THEN THE Fixture_Loader SHALL raise a `FixtureLoadError` identifying the case index and missing field.
8. IF the `expected` field contains a value other than `activate` or `no_activate`, THEN THE Fixture_Loader SHALL raise a `FixtureLoadError` identifying the case and invalid value.
9. IF the YAML file is not valid YAML, THEN THE Fixture_Loader SHALL raise a `FixtureLoadError` with the parse error detail.
10. THE Fixture_Loader SHALL require the fixture file to contain at least one `PromptCase`; IF the `cases` list is empty or absent, THEN THE Fixture_Loader SHALL raise a `FixtureLoadError`.

---

### Requirement 4: Activation Checking

**User Story:** As a developer, I want each prompt to be evaluated by an LLM judge, so that activation decisions reflect the same semantic reasoning an AI agent would use.

#### Acceptance Criteria

1. THE Activation_Checker SHALL call an LLM via `litellm` with a structured prompt containing the skill's `name`, `description`, `when_to_use`, and the test prompt.
2. THE Activation_Checker SHALL parse the LLM response as JSON and extract a `decision` field with value `"activate"` or `"no_activate"`.
3. THE Activation_Checker SHALL extract a `reasoning` field from the LLM response and include it in the returned `CheckResult`.
4. THE Activation_Checker SHALL record the latency of the LLM call in milliseconds in the returned `CheckResult`.
5. WHEN the LLM response is not valid JSON or is missing required fields, THE Activation_Checker SHALL retry the call once.
6. IF the retry also fails to return valid JSON, THEN THE Activation_Checker SHALL raise a `CheckerError`.
7. IF the LLM API call raises an exception (timeout, auth error, rate limit), THEN THE Activation_Checker SHALL raise a `CheckerError` with the underlying error detail.
8. THE Activation_Checker SHALL read API credentials exclusively from environment variables; THE Activation_Checker SHALL NOT accept API keys as function parameters or from config files.
9. THE Activation_Checker SHALL set `passed = True` in the returned `CheckResult` if and only if `actual == expected`.

---

### Requirement 5: Test Runner

**User Story:** As a developer, I want the harness to run all prompt cases and produce a complete summary, so that I get a full picture of skill activation accuracy in a single execution.

#### Acceptance Criteria

1. THE Runner SHALL execute activation checks for all `PromptCase` items in the fixture sequentially.
2. WHEN an activation check raises a `CheckerError`, THE Runner SHALL record the case as an error and continue processing remaining cases without aborting.
3. THE Runner SHALL produce a `RunSummary` where `total` equals the number of input `PromptCase` items.
4. THE Runner SHALL produce a `RunSummary` where `passed + failed + errors == total`.
5. THE Runner SHALL record the total wall-clock duration of the run in milliseconds in the `RunSummary`.

---

### Requirement 6: Result Reporting

**User Story:** As a developer, I want clear pass/fail output in my terminal and a non-zero exit code on failures, so that the harness integrates naturally with CI pipelines.

#### Acceptance Criteria

1. THE Reporter SHALL print a result line for each prompt case showing the case ID, expected outcome, actual outcome, and pass/fail status.
2. THE Reporter SHALL print a summary line showing total, passed, failed, and error counts.
3. WHEN `--verbose` is set, THE Reporter SHALL print the LLM's reasoning for each prompt case below its result line.
4. THE Reporter SHALL return exit code `0` when all cases passed.
5. THE Reporter SHALL return exit code `1` when one or more cases failed or errored.
6. THE Reporter SHALL use distinct visual markers for passed cases (e.g. `✓`), failed cases (e.g. `✗`), and error cases (e.g. `!`).

---

### Requirement 7: Skill-Agnostic Design

**User Story:** As a developer, I want the harness to work with any SKILL.md file, not just the `springboot-openapi-generator`, so that I can reuse it across all skills in a project.

#### Acceptance Criteria

1. THE Harness SHALL NOT contain any hard-coded references to a specific skill name, skill path, or skill domain.
2. THE Harness SHALL derive all skill-specific context exclusively from the loaded `SkillDefinition` at runtime.
3. THE Harness SHALL accept any valid fixture file regardless of which skill it targets, provided the fixture conforms to the schema defined in Requirement 3.

---

### Requirement 8: Project Layout and Entry Point

**User Story:** As a developer, I want a clear project layout with a single entry point, so that I can run the harness with a simple command.

#### Acceptance Criteria

1. THE Harness source code SHALL be placed in the `test/` directory at the project root.
2. THE Harness SHALL provide a single CLI entry point at `test/test_skill.py` that can be invoked with `python test/test_skill.py --skill <path> --fixture <path>`.
3. THE Harness SHALL declare its Python dependencies in a `test/requirements.txt` file.
4. THE Harness module code SHALL be organised under `test/harness/` as a Python package, with `test_skill.py` as the top-level entry point that imports from `test/harness/`.
5. THE Harness test suite SHALL be placed under `test/tests/` and SHALL be runnable with `pytest test/tests/`.
