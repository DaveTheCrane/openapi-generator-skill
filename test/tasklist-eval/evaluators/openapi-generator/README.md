# openapi-generator evaluators

Example evaluators for the `springboot-openapi-generator` skill. They check
whether a tasklist plans to *generate* the server and client code with the
OpenAPI generator Maven plugin rather than hand-writing it. Results from this
folder carry group `openapi-generator` (JUnit classname
`tasklist-eval.openapi-generator`).

## `generator-in-pom` (binary) — `generator_in_pom.py`

PASS iff two required pattern sets both match somewhere in the tasklist:
`pom-modified` (a `pom.xml` / Maven build-config task) and
`generator-mentioned` (`openapi-generator-maven-plugin`, `openapi-generator`,
or `org.openapitools`). Editing `pom.xml` without ever mentioning the generator
is a FAIL: the plan is about to hand-code everything.

## `generated-code-usage` (graded) — `generated_code_usage.py`

Scores the fraction of in-scope areas (`server`, `address-client`,
`item-client`) that consume generated code. Every area shares the `generated`
success set (`*ApiDelegate`, `target/generated-sources`, a webclient
execution, …); failures come from `server-handcoded` (`@RestController`,
mapping annotations, Lombok models) or `client-handcoded` (hand-written
`*ServiceClient`, injected `WebClient`, MockWebServer). Absent areas are
excluded from the score.

## Blind spot

Neither evaluator can verify that the Maven code-generation phase actually
runs or that the generated code compiles. A PASS means the plan took the right
shape, not that the build succeeds.

See the [main README](../../README.md#plugin-folders) for how plugin folders
are discovered and how to add your own.
