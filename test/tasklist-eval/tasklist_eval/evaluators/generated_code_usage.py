"""Graded evaluator: what fraction of in-scope areas consumed generated code?

The skill should produce, from the OpenAPI specs, three areas of code:

  * ``server``          — the REST controllers / API delegate surface
  * ``address-client``  — the Address Service client
  * ``item-client``     — the Item Service client

For each area that is *in scope* for the tasklist we classify it as:

  * GENERATED — the tasklist consumes generator output (implements a
    ``*ApiDelegate``, reads ``target/generated-sources``, adds a webclient
    execution, etc.)
  * HANDCODED — the tasklist writes that area from scratch (a hand-authored
    ``@RestController``, a hand-written ``AddressServiceClient`` with an
    injected ``WebClient`` + MockWebServer tests, hand-written Lombok models…)
  * ABSENT    — the area does not appear in this tasklist at all.

Score = (# GENERATED) / (# GENERATED + # HANDCODED); ABSENT areas are excluded.
If no areas are in scope, the score is 0.0 with a FAIL verdict.

Verdict (informational unless a graded threshold is configured):
  score >= 0.999 → PASS; 0 < score < 1 → PARTIAL; score == 0 → FAIL.
"""

from __future__ import annotations

import re

from ..models import EvaluationResult, EvaluatorKind, TaskList, Verdict
from .base import Evaluator

# --- Area-presence keywords (does this area appear at all?) ---
_AREA_PRESENCE = {
    "server": re.compile(
        r"controller|customersapi|/customers|delegate|customerservice", re.IGNORECASE
    ),
    "address-client": re.compile(r"address", re.IGNORECASE),
    "item-client": re.compile(r"\bitem", re.IGNORECASE),
}

# --- GENERATED signals (shared across areas) ---
_GENERATED_SIGNALS = [
    re.compile(r"openapi-generator", re.IGNORECASE),
    re.compile(r"generated[- ]sources", re.IGNORECASE),
    re.compile(r"target/generated-sources", re.IGNORECASE),
    re.compile(r"\w*ApiDelegate\b"),                       # implement/read a *ApiDelegate
    re.compile(r"generated\b.*\binterface|interface\b.*\bgenerated", re.IGNORECASE),
    re.compile(r"webclient\s+execution|webclient\)", re.IGNORECASE),
    re.compile(r"delegate\b.*\bgenerated|generated\b.*\bdelegate", re.IGNORECASE),
]

# --- HANDCODED signals for the server area ---
_SERVER_HANDCODED = [
    re.compile(r"@RestController", re.IGNORECASE),
    re.compile(r"create\s+.*controller", re.IGNORECASE),
    re.compile(r"customercontroller", re.IGNORECASE),
    re.compile(r"@GetMapping|@PostMapping|@RequestMapping", re.IGNORECASE),
    re.compile(r"implement\s+customerservice|create\s+.*customerservice", re.IGNORECASE),
    re.compile(r"lombok", re.IGNORECASE),                  # hand-written model classes
]

# --- HANDCODED signals for client areas ---
_CLIENT_HANDCODED = [
    re.compile(r"serviceclient\b.*@component|@component.*serviceclient", re.IGNORECASE),
    re.compile(r"inject.*webclient|webclient via constructor|injected\s+webclient", re.IGNORECASE),
    re.compile(r"mockwebserver", re.IGNORECASE),
    re.compile(r"implement\s+\w*serviceclient", re.IGNORECASE),
    re.compile(r"create\s+`?[\w.]*serviceclient", re.IGNORECASE),
]


def _any(patterns, text: str):
    for pat in patterns:
        m = pat.search(text)
        if m:
            return m.group(0)
    return None


class GeneratedCodeUsageEvaluator(Evaluator):
    """Grade the fraction of in-scope areas that consume generated code."""

    id = "generated-code-usage"
    kind = EvaluatorKind.GRADED
    description = (
        "Graded fraction of in-scope areas (server/address-client/item-client) "
        "that consume generated code rather than being hand-written."
    )

    _AREAS = ("server", "address-client", "item-client")

    def evaluate(self, tasklist: TaskList, config) -> EvaluationResult:
        # Collect per-area matching text and citation ids.
        area_text: dict[str, list[tuple[str, str]]] = {a: [] for a in self._AREAS}

        for task in tasklist.iter_tasks():
            text = task.all_text()
            tid = task.id if task.id is not None else "?"
            for area, presence in _AREA_PRESENCE.items():
                if presence.search(text):
                    area_text[area].append((tid, text))

        classifications: dict[str, str] = {}
        evidence: list[str] = []

        for area in self._AREAS:
            hits = area_text[area]
            if not hits:
                classifications[area] = "absent"
                evidence.append(f"[{area}] absent — no relevant tasks found.")
                continue

            generated_cite = None
            handcoded_cite = None
            handcoded_patterns = (
                _SERVER_HANDCODED if area == "server" else _CLIENT_HANDCODED
            )

            for tid, text in hits:
                if generated_cite is None:
                    g = _any(_GENERATED_SIGNALS, text)
                    if g:
                        generated_cite = (tid, g)
                if handcoded_cite is None:
                    h = _any(handcoded_patterns, text)
                    if h:
                        handcoded_cite = (tid, h)

            # GENERATED wins when generator signals are present; otherwise, if any
            # hand-coding signal is present, HANDCODED; else assume hand-coded
            # (the area is present but shows no generator usage).
            if generated_cite is not None:
                classifications[area] = "generated"
                evidence.append(
                    f"[{area}] generated — Task {generated_cite[0]} matched "
                    f"'{generated_cite[1]}'."
                )
            elif handcoded_cite is not None:
                classifications[area] = "handcoded"
                evidence.append(
                    f"[{area}] handcoded — Task {handcoded_cite[0]} matched "
                    f"'{handcoded_cite[1]}'."
                )
            else:
                classifications[area] = "handcoded"
                evidence.append(
                    f"[{area}] handcoded — area present but no generator signal found."
                )

        generated = [a for a, c in classifications.items() if c == "generated"]
        handcoded = [a for a, c in classifications.items() if c == "handcoded"]
        in_scope = len(generated) + len(handcoded)

        if in_scope == 0:
            return EvaluationResult(
                evaluator_id=self.id,
                kind=self.kind,
                verdict=Verdict.FAIL,
                score=0.0,
                summary="No relevant areas found (server/address-client/item-client).",
                evidence=evidence,
                details={"areas": classifications, "score": 0.0},
            )

        score = len(generated) / in_scope

        if score >= 0.999:
            verdict = Verdict.PASS
        elif score > 0:
            verdict = Verdict.PARTIAL
        else:
            verdict = Verdict.FAIL

        summary = (
            f"{len(generated)}/{in_scope} in-scope areas consume generated code "
            f"(score {score:.2f}). "
            f"generated={sorted(generated)}, handcoded={sorted(handcoded)}."
        )

        return EvaluationResult(
            evaluator_id=self.id,
            kind=self.kind,
            verdict=verdict,
            score=score,
            summary=summary,
            evidence=evidence,
            details={"areas": classifications, "score": score},
        )
