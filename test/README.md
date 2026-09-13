# Skills Test Harness

This harness tests only *whether* a skill is picked up (activated), not what it
does once it's created. In other words, it verifies activation behavior, not the
correctness of any output the skill produces.

## Scope / status

Currently covers activation only. The harness has been run end to end, but it
does not yet exercise what a skill does after it activates.

## Running

Run from the project root:

```
python test/test_skill.py --skill springboot-openapi-generator/SKILL.md --fixture test/fixtures/springboot-openapi-generator.yaml
```

## Configuration

Configuration is resolved with the following precedence (later sources override
earlier ones):

```
harness.yaml (project root)  <  environment variables  <  CLI flags
```

Available settings:

| Key / flag     | Description                                                        |
| -------------- | ------------------------------------------------------------------ |
| `skill`        | Path to the skill's `SKILL.md`.                                    |
| `fixture`      | Path to the fixture describing the activation scenario.            |
| `model`        | Judge model used to evaluate activation.                          |
| `timeout`      | Request timeout in seconds (1–300).                               |
| `verbose`      | Enable verbose output.                                            |
| `api_base`     | Base URL for the model provider/endpoint.                        |
| `extra_params` | `harness.yaml`-only mapping forwarded to litellm.                |
| `report_format` | Output report format: `text` (default), `json`, or `junit`. |
| `report_file`   | Optional path to write the report to instead of stdout.      |

Environment variables:

- `SKILL_HARNESS_MODEL` — overrides `model`.
- `SKILL_HARNESS_API_BASE` — overrides `api_base`.
- `SKILL_HARNESS_REPORT_FORMAT` — overrides `report_format`.
- `SKILL_HARNESS_REPORT_FILE` — overrides `report_file`.

By default the judge model is a cloud model (`claude-3-5-haiku-20241022`), which
needs the corresponding provider API key in the environment (e.g.
`ANTHROPIC_API_KEY`).

## Report formats

The harness can emit results in three formats via `--report-format
{text,json,junit}` (default `text`). Use `--report-file PATH` to write the
report to a file instead of stdout; in that case a short `Report written to
<path>` confirmation is printed to stdout.

- `text`: human-readable console output, with per-case ✓/✗/! markers, a Results
  summary line, and a metadata footer.
- `json`: a machine-readable document with `tool`, `metadata` (model,
  timeout_seconds, api_base, timestamp, duration_ms), `summary`, and per-case
  `results` (including `reasoning`, `latency_ms`, and `error`). Good for
  dashboards or tracking accuracy across models over time.
- `junit`: JUnit XML for CI systems. It is CI-agnostic and consumed natively by
  most CI platforms (e.g. GitLab, Jenkins, CircleCI, Azure DevOps) or via a
  plugin/action. Per-case LLM reasoning is included in each testcase's
  `<system-out>` (spec-compatible; ignored by tools that don't display it). Run
  metadata (model, timeout, api_base) is emitted as testsuite `<properties>`.

The process exit code is the same regardless of format: `0` when all cases
pass, `1` if any case fails or errors — so CI gating works with any format.

Example commands:

```
# JUnit XML written to a file for CI to collect
python test/test_skill.py --report-format junit --report-file reports/skill-activation.xml

# JSON to stdout
python test/test_skill.py --report-format json
```

### Sample reports

The `sample-reports/` folder contains example output in each format, in two
sets:

- all-pass: `sample-reports/all-pass.txt`, `sample-reports/all-pass.json`,
  `sample-reports/all-pass.xml`
- mixed-outcomes: `sample-reports/mixed-outcomes.txt`,
  `sample-reports/mixed-outcomes.json`, `sample-reports/mixed-outcomes.xml`

The all-pass set is from a real local Ollama run. The mixed-outcomes set is
illustrative — hand-constructed to show a FAIL and an ERROR case.

## Using a local Ollama model

You can run the harness fully offline against a local Ollama model.

**Prerequisites**

- Ollama running locally (default `http://localhost:11434`).
- A model pulled locally, e.g. `ollama pull qwen3.5`.

**How LiteLLM addresses Ollama**

LiteLLM talks to Ollama via the `ollama_chat/<model>` model prefix combined with
an `api_base` pointing at your local Ollama server.

**Important: reasoning models**

Reasoning models such as `qwen3.5` perform internal "thinking" that can exhaust
the token budget and cause request timeouts. Disable it and cap output via
`extra_params`:

```yaml
extra_params:
  think: false
  num_predict: 300
```

**Ready-to-use `harness.yaml`**

This file already exists at the project root:

```yaml
skill: springboot-openapi-generator/SKILL.md
fixture: test/fixtures/springboot-openapi-generator.yaml
model: ollama_chat/qwen3.5:latest
api_base: http://localhost:11434
timeout: 120
verbose: true
extra_params:
  think: false
  num_predict: 300
```

With `harness.yaml` present at the project root, you can simply run the harness
with no flags and no cloud API key:

```
python test/test_skill.py
```

## Local vs. frontier models

> **Note:** Results reflect how the chosen judge model interprets the prompts.
> A smaller local model (e.g. `qwen3.5` via Ollama) may judge borderline or
> ambiguous prompts differently than a frontier cloud model. Treat local runs as
> a fast, offline, no-cost development loop, and use a frontier model for the more
> authoritative activation verdict. This is a model-quality consideration, not a
> harness limitation.
