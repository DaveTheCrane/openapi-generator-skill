---
inclusion: always
---
# Build and Code Generation

Part of this project's code is generated at build time (for example by Lombok and by code generators wired into the Maven build). Follow these rules whenever you build, test, or write code that touches generated types.

## Canonical build and test commands

- Always build and test with `mvn clean test`.
- Do NOT invoke `javac` or `java` directly, and do NOT compile against `target/classes` by hand. Manual compilation leaves stale `.class` files that cause conflicting bean definitions and other spurious failures on the next Maven run.
- If a build fails in a way that looks like stale state (duplicate/conflicting beans, classes that "shouldn't" be there), run `mvn clean` first, then retry.

## Code generation is part of the build

- Code generators run in the `generate-sources` phase on every build. Regenerating this code is expected to take time — slowness is NOT a reason to work around Maven.
- Never hand-edit generated sources. They are regenerated on every build and are not committed to git.

## Where generated code lives

- Generated sources live under `target/generated-sources/`, in a subfolder per generator execution.
- When a generator execution writes to its own output directory, that directory must be registered as a compile source root (e.g. via `build-helper-maven-plugin`) so the generated code is picked up. If you add another execution with a distinct output directory, add a matching source-root entry.

## Read generated types before coding against them

Before writing production code or tests that use a generated model or interface, READ the actual generated `.java` file under `target/generated-sources` rather than inferring the type from a specification or from the design document. Real generated signatures often differ from the abstract descriptions in a design (nullable wrappers, exact return types, package/name collisions, and so on). Account for this during the design phase.

## Keep the design's dependency and model notes honest

A design document's list of dependencies and its simplified model shapes are a starting point, not ground truth: generated code can pull in additional transitive dependencies. When `mvn compile` reveals a missing dependency, add it and prefer to note it back in the design.

## Generator-specific guidance

Details specific to a particular code generator (exact package layout, model type quirks, error-handling conventions) belong in the relevant skill rather than here. For OpenAPI-generated services, see the `springboot-openapi-generator` skill.
