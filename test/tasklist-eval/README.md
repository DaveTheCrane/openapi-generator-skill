# Tasklist Evaluation Framework

This framework evaluates a Kiro spec-driven `tasks.md` file to judge whether a
*skill* was applied correctly — using only signals that are visible in the
tasklist itself. Inspecting a tasklist is much cheaper than generating and
compiling the full project, so this is a fast first-pass signal for any skill
used within the Kiro spec-driven workflow.

The framework is skill-agnostic: you write evaluators for whatever skill you are
testing and register them by id. The evaluators that ship here are built-in
*examples* for the `springboot-openapi-generator` skill; they demonstrate the
patterns you would follow for your own.

Task completion state (the `- [ ]` / `- [x]` checkbox markers) is parsed and
stored, but **deliberately ignored** when computing verdicts. Whether a task is
ticked has no bearing on whether the skill chose the right approach.

## Scope and limitations

Tasklist-level evaluation tells you whether the *plan* took the intended shape —
not whether the resulting build or compile actually succeeds. The specific
signals each check looks for depend entirely on the evaluators you write, so the
blind spots are the evaluators' blind spots.

For instance, the bundled openapi-generator evaluators can tell whether the plan
chose to *generate* the server and client code via the OpenAPI generator versus
hand-writing controllers, value objects, and WebClient clients from scratch.
They cannot tell whether the Maven code-generation phase was actually navigated
correctly; that only shows up once real code is generated and compiled. Treat a
PASS here as "the plan took the right shape," not "the build succeeds."

A separate tool could later generate these tasklists from a skill plus curated
prompts; for now the framework takes any `tasks.md` as input regardless of where
it came from.

## Supported input formats

Kiro has emitted tasklists in a couple of shapes across versions; both parse:

- **Flat style** — `## Task N: Title` headers, each followed by `- [ ] ...`
  detail bullets. The bullets are treated as *body detail* of task `N`, not as
  separate sub-tasks. (See `samples/skill-present-and-activated--tasks.md`.)
- **Nested style** — top-level `- [ ] N. Title` checkbox items with indented
  `- [ ] N.M ...` sub-tasks; deeper `- ...` lines are body detail of their
  parent sub-task. (See the other two samples.)

Optional sections are all tolerated whether present or absent:

- `## Overview` prose
- `_Requirements: 1.1, 2.3_` references attached to a task
- optional-task markers like `- [ ]* 2.7`
- `## Notes` bullets
- a `## Task Dependency Graph` fenced ```json block (malformed JSON → ignored,
  never a crash)

## Running

Run from the project root using the project venv. This is an example run against
a bundled sample:

```
python test/tasklist-eval/evaluate.py test/tasklist-eval/samples/skill-present-and-activated--tasks.md
```

Write a JUnit report to a file for CI to collect:

```
python test/tasklist-eval/evaluate.py <path/to/tasks.md> --report-format junit --report-file reports/eval.xml
```

Run only one evaluator:

```
python test/tasklist-eval/evaluate.py <path> --evaluators generator-in-pom
```

### CLI help

```
python test/tasklist-eval/evaluate.py --help
```

lists every option, the available evaluator ids with their plugin group (so
`--evaluators` is discoverable), example invocations, and the supported
environment variables (including `TASKLIST_EVAL_PLUGIN_DIRS`).

## Writing evaluators

Evaluators are decoupled plugins. Each receives only the parsed `TaskList` plus
the run config and returns an `EvaluationResult` — it never imports the runner
or reporter. An evaluator declares an `id`, a `kind` (`binary` or `graded`), and
optionally a short `description`. New checks can be added without touching the
core, and the framework itself knows nothing about any particular skill: you add
evaluators specific to whatever skill you are testing.

### Plugin folders

`tasklist_eval/` holds only the generic framework (the `Evaluator` base,
`PatternSet`, `BinaryEvaluator`, `GradedEvaluator`, `Area`, the parser, runner,
reporter, and so on). Skill-specific evaluators live in plugin folders next to
the package, one folder per group:

```
test/tasklist-eval/
  tasklist_eval/            # framework
  evaluators/               # default plugin root
    openapi-generator/      # plugin group (hyphens allowed)
      generator_in_pom.py
      generated_code_usage.py
```

At startup every immediate subfolder of the plugin root is scanned (sorted,
skipping names starting with `.` or `_`), and every `*.py` file in it is
imported (sorted, skipping names starting with `_`). Each module's
`EVALUATORS = [...]` list is registered; modules without `EVALUATORS` are
skipped, so they can hold shared helpers. Plugin folders are not packages, so
use absolute imports (`from tasklist_eval.evaluators import BinaryEvaluator,
GradedEvaluator, Area, PatternSet`).

Each evaluator's `plugin_group` is its folder name. It appears as `group` in
JSON results and as the JUnit testcase classname `tasklist-eval.<group>`, and
`--help` shows it next to the id (e.g. `generator-in-pom  (openapi-generator)`).

The default plugin root is `test/tasklist-eval/evaluators`; set
`TASKLIST_EVAL_PLUGIN_DIRS` to use other roots instead (see
[Configuration](#configuration)). A missing plugin directory, a plugin that
fails to import, an `EVALUATORS` value of the wrong type, or a duplicate
evaluator id prints `Plugin error: ...` to stderr and exits with code `2`.

- **binary** evaluators return PASS or FAIL. A failing binary evaluator gates
  the overall verdict to FAIL.
- **graded** evaluators return a score in `[0, 1]` and are informational by
  default (see the verdict rule below).

You can subclass `Evaluator` directly, but most checks are just "which regexes
fire in which tasks". For those, `tasklist_eval.evaluators` provides generic,
declarative building blocks, so a new evaluator is configuration rather than
code.

### `PatternSet`

A named, ordered group of regexes. String patterns are compiled with
`re.IGNORECASE` by default (override with `flags=`); pre-compiled `re.Pattern`
objects keep their own flags, so one set can mix case-insensitive and
case-sensitive patterns. `search(text)` returns the first matched substring,
trying patterns in order. An empty name, an empty pattern list, or an invalid
regex raises `ValueError` naming the set and the pattern.

The set name is what shows up in reports: evidence bullets say
`Task 4.2 matched '...' (client-handcoded)` rather than just the matched text,
and graded results record the winning set per area in JSON
`details["decided_by"]`. Pick names that explain the signal.

### `BinaryEvaluator`

Configured with `require` and (optionally) `forbid` lists of pattern sets.
PASS iff every `require` set matches in at least one task **and** no `forbid`
set matches anywhere. Each task contributes at most one match per set, cited as
`Task {id}: {set} — matched '...'` (forbid hits are tagged `(forbidden)`).
`details` carries per-set `matched`/`role`/`matches`, plus `missing` and
`forbidden_hits`. An optional `summaries` dict maps outcomes to summary text:
`pass`, `missing:<set>` (exactly that one required set missing),
`missing:all`, and `fail` as the fallback.

### `GradedEvaluator`

Configured with a list of `Area`s. Each area has a `presence` set (does this
area appear at all?) and lists of `success` and `failure` sets, which are
scanned only in the tasks where the area is present. Per area:

- no presence hits → `absent` (excluded from the score);
- only a success or only a failure set hits → that label;
- both hit → `conflict_winner` decides (`"success"` by default);
- present but neither hits → `unmatched_present` decides (`"failure"` by
  default).

`success_label` / `failure_label` name the classifications in evidence, the
summary, and `details["areas"]`. Score = success / (success + failure);
`score >= pass_threshold` (default `0.999`) is PASS, any other non-zero score
is PARTIAL, and 0 (or no in-scope areas) is FAIL.

### Example: a new evaluator

A skill that should drive test-first development might add a plugin module
`evaluators/my-skill/uses_tdd.py`:

```python
from tasklist_eval.evaluators import BinaryEvaluator, PatternSet

uses_tdd = BinaryEvaluator(
    id="uses-tdd",
    description="PASS iff the plan writes failing tests before the implementation.",
    require=[PatternSet("red-green", [r"red[- /]green", r"failing test first"])],
    forbid=[PatternSet("tests-skipped", [r"skip (the )?tests"])],
    summaries={"pass": "Plan follows red-green TDD."},
)

EVALUATORS = [uses_tdd]
```

It is discovered at the next run, listed in `--help` under group `my-skill`,
and selectable via `--evaluators uses-tdd`. For programmatic use you can
instead call `EvaluatorRegistry.register(uses_tdd)` on a registry directly.

### Built-in examples

The two evaluators below ship as **example evaluators for the
`springboot-openapi-generator` skill**, in the `openapi-generator` plugin group.
Both are thin declarative instances of the generic classes (see
`evaluators/openapi-generator/generator_in_pom.py` and
`generated_code_usage.py`, plus that folder's `README.md`).

#### `generator-in-pom` (binary, example)

PASSes only when the tasklist **both** (1) modifies `pom.xml` / configures the
Maven build (the `pom-modified` set) **and** (2) mentions the OpenAPI generator
(`openapi-generator-maven-plugin`, `openapi-generator`, or `org.openapitools`;
the `generator-mentioned` set). A plan that edits `pom.xml` but never adds the
generator — i.e. it is about to hand-code everything — is a FAIL.

#### `generated-code-usage` (graded, example)

Of the three areas the skill should produce — `server` (REST controllers /
`*ApiDelegate` surface), `address-client`, and `item-client` — this measures the
fraction that actually *consume* generated code rather than being hand-written.
Each in-scope area is classified `generated`, `handcoded`, or `absent`, and the
score is `generated / (generated + handcoded)` (absent areas excluded). All
areas share one `generated` success set; the failure sets are
`server-handcoded` (hand-written `@RestController`s, Lombok models, …) and
`client-handcoded` (hand-written `*ServiceClient`s, injected `WebClient`,
MockWebServer tests), so a report tells you which kind of hand-coding was
detected. A plan
that generates the server delegate but hand-codes both clients scores ~0.33
(PARTIAL); a fully generated plan scores 1.0 (PASS); a fully hand-coded plan
scores 0.0 (FAIL).

## Overall verdict rule

- A **binary** evaluator that FAILs makes the overall verdict FAIL.
- **Graded** evaluators are *informational* by default and do not affect the
  overall verdict — unless you pass `--graded-threshold FLOAT` (0..1). When set,
  any graded score below the threshold becomes a FAIL and gates the overall
  verdict.
- Otherwise the overall verdict is PASS.

## Configuration

Configuration is resolved with the following precedence (later overrides
earlier):

```
tasklist-eval.yaml (cwd)  <  environment variables  <  CLI flags
```

| Key / flag          | Description                                                      |
| ------------------- | --------------------------------------------------------------- |
| `tasklist`          | Path to the tasklist markdown (positional arg or `--tasklist`). |
| `report_format`     | `text` (default), `json`, or `junit`.                           |
| `report_file`       | Optional path to write the report to instead of stdout.         |
| `evaluators`        | Subset of evaluator ids to run (`--evaluators a,b`).            |
| `graded_threshold`  | If set (0..1), graded scores below it FAIL and gate overall.    |
| `verbose`           | Extra output.                                                   |

Environment variables:

- `TASKLIST_EVAL_REPORT_FORMAT` — overrides `report_format`.
- `TASKLIST_EVAL_REPORT_FILE` — overrides `report_file`.
- `TASKLIST_EVAL_PLUGIN_DIRS` — `os.pathsep`-separated list of plugin roots
  (`:` on macOS/Linux, `;` on Windows). Replaces the default
  `test/tasklist-eval/evaluators`. Environment-only: the evaluator registry is
  built before CLI args are parsed.

Validation raises a clear error when: the tasklist path is missing or not a
readable file, the report format is unknown, a `--report-file`'s parent
directory does not exist, `graded_threshold` is outside `[0, 1]`, or an unknown
evaluator id is requested (the error lists the valid ids).

## Report formats

Select via `--report-format {text,json,junit}` (default `text`). Use
`--report-file PATH` to write to a file instead of stdout; a short
`Report written to <path>` confirmation is printed to stdout in that case.

- `text`: human-readable console output — a `✓`/`✗`/`~` marker per evaluator
  (PASS / FAIL / PARTIAL), the kind, the graded score, the summary, indented
  evidence bullets, an `Overall:` line, and a metadata footer.
- `json`: `{ tool, metadata (tasklist, timestamp, duration_ms), overall,
  results[] }` where each result carries `evaluator_id`, `group` (the plugin
  folder name), `kind`, `verdict`, `score`, `summary`, `evidence`, and
  structured `details`.
- `junit`: JUnit XML for CI. One `<testcase>` per evaluator, with classname
  `tasklist-eval.<group>` (e.g. `tasklist-eval.openapi-generator`); a FAIL emits a
  `<failure>` whose `type` is `binary` or `graded`. JUnit has no native
  "partial" state, so a **PARTIAL evaluator is emitted as a passing testcase**
  (no `<failure>`) with its score and summary preserved in `<system-out>` —
  that way the partial signal is not lost but CI does not spuriously fail on it.
  Run metadata (tasklist path, tool) is emitted as testsuite `<properties>`.

The process exit code is format-independent: `0` when the overall verdict is
PASS, `1` otherwise — so CI gating works with any format. A plugin loading
error (see [Plugin folders](#plugin-folders)) exits with `2` before any
evaluation runs.

### Sample reports

`sample-reports/` holds example output generated from two of the bundled
samples:

- `activated.{txt,json,xml}` — the fully generated plan (overall PASS).
- `not-present.{txt,json,xml}` — the hand-coded plan (overall FAIL).

## Tests

```
.venv/bin/pytest test/tasklist-eval/tests/
```

The suite covers the parser on all three sample formats (ids, nesting, optional
markers, requirements, notes/dependency-graph present/absent/malformed, varied
checkbox markers), both example evaluators against the expected oracle verdicts
(including a synthetic partial-success tasklist), the generic `PatternSet`,
`BinaryEvaluator`, and `GradedEvaluator` building blocks (including a
non-openapi example evaluator), config precedence and
validation, the CLI help output (evaluator ids, examples, and environment
sections), the runner's overall-verdict and threshold-gating logic, and the
reporter in all three formats.
