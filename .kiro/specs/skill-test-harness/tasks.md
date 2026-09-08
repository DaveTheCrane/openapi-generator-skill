# Implementation Plan: Skill Test Harness

## Overview

Build the Python skill test harness incrementally, starting with the project skeleton and data models, then adding each component in dependency order (loaders → checker → runner → reporter → CLI). Property-based tests are introduced alongside each component so correctness is validated early.

## Tasks

- [x] 1. Set up project structure, dependencies, and core data models
  - Create `test/` directory with `test/harness/` package (`__init__.py`) and `test/tests/` directory
  - Create `test/requirements.txt` with pinned versions: `litellm>=1.40`, `pyyaml>=6.0`, `pytest>=8.0`, `hypothesis>=6.100`
  - Define all dataclasses and enums in `test/harness/models.py`: `HarnessConfig`, `SkillDefinition`, `PromptCase`, `ExpectedOutcome`, `ActivationResult`, `CheckResult`, `RunSummary`
  - Define custom exception classes `ConfigError`, `SkillLoadError`, `FixtureLoadError`, `CheckerError` in `test/harness/exceptions.py`
  - _Requirements: 8.3, 8.4_

- [x] 2. Implement Config Loader
  - [x] 2.1 Implement `test/harness/config.py` with `load_config() -> HarnessConfig`
    - Parse CLI arguments (`--skill`, `--fixture`, `--model`, `--timeout`, `--verbose`) using `argparse`
    - Load optional `harness.yaml` from current working directory using `yaml.safe_load`
    - Apply precedence: config file < `SKILL_HARNESS_MODEL` env var < CLI arguments
    - Validate `skill_path` and `fixture_path` exist and are readable; raise `ConfigError` otherwise
    - Validate `timeout_seconds` is in `[1, 300]`; raise `ConfigError` otherwise
    - _Requirements: 1.1–1.11_

  - [ ]* 2.2 Write property test for config precedence (Property 1)
    - **Property 1: Config precedence — CLI overrides file**
    - **Validates: Requirements 1.8**
    - Use `hypothesis` to generate arbitrary config key-value pairs in both file and CLI; assert CLI always wins

  - [ ]* 2.3 Write property test for timeout validation (Property 2)
    - **Property 2: Timeout validation accepts valid range, rejects invalid range**
    - **Validates: Requirements 1.11**
    - Use `hypothesis.strategies.integers()` to generate values; assert accept iff `1 <= N <= 300`

- [x] 3. Implement Skill Loader
  - [x] 3.1 Implement `test/harness/skill_loader.py` with `load_skill(path: str) -> SkillDefinition`
    - Read the file at `path`
    - Parse YAML front matter (delimited by `---`) to extract `description`
    - Extract `## When to Use` section body from the markdown
    - Store full file content in `raw_content`
    - Raise `SkillLoadError` if `description` is absent from front matter
    - Raise `SkillLoadError` if `## When to Use` section is absent
    - _Requirements: 2.1–2.6_

  - [ ]* 3.2 Write property test for skill field extraction (Property 3)
    - **Property 3: Skill fields are correctly extracted**
    - **Validates: Requirements 2.2, 2.3, 2.6**
    - Use `hypothesis` to generate synthetic SKILL.md content; assert extracted fields match generated values and `raw_content` is a round-trip

- [x] 4. Implement Fixture Loader
  - [x] 4.1 Implement `test/harness/fixture_loader.py` with `load_fixture(path: str) -> list[PromptCase]`
    - Parse YAML file using `yaml.safe_load`
    - Validate each case has `id`, `prompt`, and `expected`; raise `FixtureLoadError` for any missing field
    - Validate `expected` is `"activate"` or `"no_activate"`; raise `FixtureLoadError` for invalid values
    - Validate `id` values are unique; raise `FixtureLoadError` identifying any duplicate
    - Treat `notes` as optional
    - Raise `FixtureLoadError` if `cases` is empty or absent
    - _Requirements: 3.1–3.10_

  - [ ]* 4.2 Write property test for loaded PromptCase validity (Property 4)
    - **Property 4: All loaded PromptCases satisfy the schema**
    - **Validates: Requirements 3.2, 3.3, 3.4**
    - Use `hypothesis` to generate valid fixture content; assert all returned `PromptCase` objects satisfy schema invariants

  - [ ]* 4.3 Write property test for duplicate ID rejection (Property 5)
    - **Property 5: Fixture loading rejects duplicate IDs**
    - **Validates: Requirements 3.6**
    - Generate fixture content where two cases share the same ID; assert `FixtureLoadError` is raised

  - [ ]* 4.4 Write property test for missing/invalid field rejection (Property 6)
    - **Property 6: Fixture loading rejects invalid or missing required fields**
    - **Validates: Requirements 3.7, 3.8**
    - Generate cases with each required field absent or with invalid `expected` values; assert `FixtureLoadError` raised in all cases

  - [ ]* 4.5 Write property test for valid fixture round-trip (Property 16)
    - **Property 16: Any conforming fixture file loads without error**
    - **Validates: Requirements 7.3, 3.1**
    - Generate arbitrary valid fixture YAML; assert `load_fixture` succeeds and returns non-empty list

- [x] 5. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Activation Checker
  - [x] 6.1 Implement `test/harness/activation_checker.py` with `check_activation(...) -> CheckResult`
    - Build the system prompt and user message template as defined in the design
    - Call `litellm.completion()` with the configured model and timeout
    - Parse the JSON response; retry once on `json.JSONDecodeError` or missing fields
    - Map `"decision"` to `ActivationResult`; extract `"reasoning"`
    - Record `latency_ms` using `time.perf_counter()`
    - Set `passed = (actual == expected)`
    - Raise `CheckerError` on API exception or exhausted retries
    - _Requirements: 4.1–4.9_

  - [ ]* 6.2 Write property test for LLM response mapping (Property 7)
    - **Property 7: LLM response is correctly mapped to CheckResult**
    - **Validates: Requirements 4.2, 4.3, 4.4**
    - Mock `litellm.completion` using `hypothesis`-generated valid JSON responses; assert all fields map correctly

  - [ ]* 6.3 Write property test for CheckResult.passed correctness (Property 8)
    - **Property 8: CheckResult.passed is determined solely by actual vs expected**
    - **Validates: Requirements 4.9**
    - Enumerate all four `(actual, expected)` combinations; assert `passed == (actual == expected)`

  - [ ]* 6.4 Write property test for LLM judge prompt completeness (Property 9)
    - **Property 9: LLM judge prompt contains all skill and prompt fields**
    - **Validates: Requirements 4.1, 7.2**
    - Mock `litellm.completion`, capture call arguments; use `hypothesis` to generate skill/prompt pairs and assert all fields appear in the message

- [x] 7. Implement Test Runner
  - [x] 7.1 Implement `test/harness/runner.py` with `run(cases, skill, config) -> RunSummary`
    - Iterate over all `PromptCase` items sequentially
    - Call `check_activation()` for each; catch `CheckerError` per case and record as error without aborting
    - Accumulate `CheckResult` list; compute `passed`, `failed`, `errors`
    - Record wall-clock `duration_ms`
    - _Requirements: 5.1–5.5_

  - [ ]* 7.2 Write property test for runner count consistency (Property 10)
    - **Property 10: Runner processes every case and counts are consistent**
    - **Validates: Requirements 5.1, 5.3, 5.4**
    - Mock `check_activation` with `hypothesis`-generated pass/fail/error distributions; assert `total == N` and `passed + failed + errors == total`

  - [ ]* 7.3 Write property test for runner error isolation (Property 11)
    - **Property 11: Runner error isolation — a single failing case does not abort the run**
    - **Validates: Requirements 5.2**
    - Mock some cases to raise `CheckerError`; assert all non-erroring cases still appear in results

- [x] 8. Implement Result Reporter
  - [x] 8.1 Implement `test/harness/reporter.py` with `report(summary: RunSummary, verbose: bool) -> int`
    - Print a result line per case with ID, expected, actual, and `✓`/`✗`/`!` marker
    - Print a summary line with total/passed/failed/error counts
    - Print LLM reasoning per case when `verbose=True`
    - Return `0` if `failed == 0 and errors == 0`, else `1`
    - _Requirements: 6.1–6.6_

  - [ ]* 8.2 Write property test for reporter result line coverage (Property 12)
    - **Property 12: Reporter output contains a line for every result**
    - **Validates: Requirements 6.1**
    - Generate `RunSummary` with N results using `hypothesis`; assert N result lines in output, each containing the case ID

  - [ ]* 8.3 Write property test for reporter summary counts (Property 13)
    - **Property 13: Reporter output contains correct counts in summary line**
    - **Validates: Requirements 6.2**
    - Generate `RunSummary` with known counts; assert all counts appear in output

  - [ ]* 8.4 Write property test for verbose reasoning inclusion (Property 14)
    - **Property 14: Verbose mode includes reasoning for every case**
    - **Validates: Requirements 6.3**
    - Generate summaries with reasoning strings; assert all appear in verbose output

  - [ ]* 8.5 Write property test for exit code logic (Property 15)
    - **Property 15: Exit code reflects pass/fail status**
    - **Validates: Requirements 6.4, 6.5**
    - Generate all-passing summaries → assert exit 0; generate summaries with any failure/error → assert exit 1

- [x] 9. Implement CLI entry point and wire components
  - [x] 9.1 Implement `test/test_skill.py` as the CLI entry point
    - Import and call `load_config()`, `load_skill()`, `load_fixture()`, `run()`, `report()`
    - Call `sys.exit()` with the reporter's return value
    - Add `if __name__ == "__main__": main()` guard
    - _Requirements: 8.1, 8.2_

  - [x] 9.2 Create a sample fixture file for the `springboot-openapi-generator` skill
    - Write `test/fixtures/springboot-openapi-generator.yaml` with at least 6 prompt cases (3 should-activate, 3 should-not-activate) drawn from the skill's `## When to Use` section
    - _Requirements: 3.1–3.5_

- [x] 10. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

---

## Notes

- Tasks marked with `*` are optional test sub-tasks and can be skipped for a faster MVP
- All property tests use `hypothesis` and require at least 100 iterations (Hypothesis default)
- Integration tests (real LLM calls) are opt-in via `SKILL_HARNESS_INTEGRATION_TESTS=1` and are not included in this task list — they can be added after the core harness is working
- API keys must be provided via environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, etc.); the harness never reads or stores keys

---

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1"] },
    { "id": 2, "tasks": ["2.2", "2.3", "3.2", "4.2", "4.3", "4.4", "4.5"] },
    { "id": 3, "tasks": ["6.1"] },
    { "id": 4, "tasks": ["6.2", "6.3", "6.4", "7.1"] },
    { "id": 5, "tasks": ["7.2", "7.3", "8.1"] },
    { "id": 6, "tasks": ["8.2", "8.3", "8.4", "8.5", "9.1"] },
    { "id": 7, "tasks": ["9.2"] }
  ]
}
```
