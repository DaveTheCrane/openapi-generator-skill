"""Binary evaluator: did the tasklist add the OpenAPI generator to pom.xml?

PASS iff BOTH conditions hold, else FAIL:

  1. There is evidence of a ``pom.xml`` / Maven build-config task, AND
  2. The generator is mentioned (``openapi-generator-maven-plugin``,
     ``openapi-generator`` / ``openapi generator``, or ``org.openapitools``).

Rationale: the skill's whole point is to generate the server + client code via
the OpenAPI generator Maven plugin. A tasklist that edits ``pom.xml`` but never
mentions the generator (both hand-coding samples) is a FAIL; one that adds the
plugin (the activated sample) is a PASS.
"""

from __future__ import annotations

import re

from ..models import EvaluationResult, EvaluatorKind, TaskList, Verdict
from .base import Evaluator

# pom.xml or a Maven build-config task.
_POM_RE = re.compile(r"pom\.xml", re.IGNORECASE)
_MAVEN_BUILD_RE = re.compile(
    r"maven\s+dependenc|maven\s+build|build[- ]helper|build\s+config|dependenc(?:y|ies)\s+to\s+pom",
    re.IGNORECASE,
)
# Generator mentions.
_GENERATOR_PATTERNS = [
    re.compile(r"openapi-generator-maven-plugin", re.IGNORECASE),
    re.compile(r"openapi[- ]?generator", re.IGNORECASE),
    re.compile(r"org\.openapitools", re.IGNORECASE),
]


class GeneratorInPomEvaluator(Evaluator):
    """Detect whether the tasklist adds the OpenAPI generator to pom.xml."""

    id = "generator-in-pom"
    kind = EvaluatorKind.BINARY
    description = (
        "PASS iff the tasklist both configures pom.xml/the Maven build and "
        "mentions the OpenAPI generator plugin."
    )

    def evaluate(self, tasklist: TaskList, config) -> EvaluationResult:
        pom_matches: list[str] = []
        generator_matches: list[str] = []
        evidence: list[str] = []

        for task in tasklist.iter_tasks():
            text = task.all_text()
            tid = task.id if task.id is not None else "?"

            if _POM_RE.search(text) or _MAVEN_BUILD_RE.search(text):
                phrase = self._first_match(text, [_POM_RE, _MAVEN_BUILD_RE])
                pom_matches.append(phrase)
                evidence.append(f"Task {tid}: pom/build config — matched '{phrase}'")

            for pat in _GENERATOR_PATTERNS:
                m = pat.search(text)
                if m:
                    generator_matches.append(m.group(0))
                    evidence.append(
                        f"Task {tid}: generator mention — matched '{m.group(0)}'"
                    )
                    break

        pom_modified = bool(pom_matches)
        generator_mentioned = bool(generator_matches)
        passed = pom_modified and generator_mentioned

        if passed:
            summary = (
                "pom.xml is modified to add the OpenAPI generator "
                "(openapi-generator plugin detected)."
            )
        elif pom_modified and not generator_mentioned:
            summary = (
                "pom.xml/build is modified but the OpenAPI generator is never "
                "mentioned — code appears to be hand-written instead of generated."
            )
        elif generator_mentioned and not pom_modified:
            summary = (
                "The OpenAPI generator is mentioned but no pom.xml/build task was "
                "found to register it."
            )
        else:
            summary = "No pom.xml/build task and no OpenAPI generator mention found."

        if not evidence:
            evidence.append("No matching pom.xml or generator references in any task.")

        return EvaluationResult(
            evaluator_id=self.id,
            kind=self.kind,
            verdict=Verdict.PASS if passed else Verdict.FAIL,
            score=None,
            summary=summary,
            evidence=evidence,
            details={
                "pom_modified": pom_modified,
                "generator_mentioned": generator_mentioned,
                "matches": sorted(set(pom_matches + generator_matches)),
            },
        )

    @staticmethod
    def _first_match(text: str, patterns) -> str:
        for pat in patterns:
            m = pat.search(text)
            if m:
                return m.group(0)
        return ""
