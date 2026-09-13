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

Environment variables:

- `SKILL_HARNESS_MODEL` — overrides `model`.
- `SKILL_HARNESS_API_BASE` — overrides `api_base`.

By default the judge model is a cloud model (`claude-3-5-haiku-20241022`), which
needs the corresponding provider API key in the environment (e.g.
`ANTHROPIC_API_KEY`).

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
