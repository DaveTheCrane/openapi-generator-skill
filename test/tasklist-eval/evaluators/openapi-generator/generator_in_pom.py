"""Binary evaluator: did the tasklist add the OpenAPI generator to pom.xml?

PASS iff BOTH conditions hold, else FAIL:

  1. There is evidence of a ``pom.xml`` / Maven build-config task, AND
  2. The generator is mentioned (``openapi-generator-maven-plugin``,
     ``openapi-generator`` / ``openapi generator``, or ``org.openapitools``).

Rationale: the skill's whole point is to generate the server + client code via
the OpenAPI generator Maven plugin. A tasklist that edits ``pom.xml`` but never
mentions the generator (both hand-coding samples) is a FAIL; one that adds the
plugin (the activated sample) is a PASS.

This is a thin declarative instance of the generic
:class:`~tasklist_eval.evaluators.binary.BinaryEvaluator`, built for the
``springboot-openapi-generator`` skill. It is a plugin module: the framework
discovers it at startup and registers everything listed in ``EVALUATORS``.
"""

from __future__ import annotations

from tasklist_eval.evaluators import BinaryEvaluator, PatternSet

# pom.xml or a Maven build-config task.
POM_MODIFIED = PatternSet(
    "pom-modified",
    [
        r"pom\.xml",
        r"maven\s+dependenc|maven\s+build|build[- ]helper|build\s+config|dependenc(?:y|ies)\s+to\s+pom",
    ],
)

# Generator mentions.
GENERATOR_MENTIONED = PatternSet(
    "generator-mentioned",
    [
        r"openapi-generator-maven-plugin",
        r"openapi[- ]?generator",
        r"org\.openapitools",
    ],
)

SUMMARIES = {
    "pass": (
        "pom.xml is modified to add the OpenAPI generator "
        "(openapi-generator plugin detected)."
    ),
    "missing:generator-mentioned": (
        "pom.xml/build is modified but the OpenAPI generator is never "
        "mentioned — code appears to be hand-written instead of generated."
    ),
    "missing:pom-modified": (
        "The OpenAPI generator is mentioned but no pom.xml/build task was "
        "found to register it."
    ),
    "missing:all": "No pom.xml/build task and no OpenAPI generator mention found.",
}


class GeneratorInPomEvaluator(BinaryEvaluator):
    """Detect whether the tasklist adds the OpenAPI generator to pom.xml."""

    def __init__(self) -> None:
        super().__init__(
            id="generator-in-pom",
            description=(
                "PASS iff the tasklist both configures pom.xml/the Maven build and "
                "mentions the OpenAPI generator plugin."
            ),
            require=[POM_MODIFIED, GENERATOR_MENTIONED],
            summaries=SUMMARIES,
        )


EVALUATORS = [GeneratorInPomEvaluator()]
