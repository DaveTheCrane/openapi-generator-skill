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

GENERATED wins when generator signals are present; otherwise, if any
hand-coding signal is present, HANDCODED; else the area is assumed hand-coded
(it is present but shows no generator usage).

Score = (# GENERATED) / (# GENERATED + # HANDCODED); ABSENT areas are excluded.
If no areas are in scope, the score is 0.0 with a FAIL verdict.

Verdict (informational unless a graded threshold is configured):
  score >= 0.999 → PASS; 0 < score < 1 → PARTIAL; score == 0 → FAIL.

This is a thin declarative instance of the generic
:class:`~tasklist_eval.evaluators.graded.GradedEvaluator`, built for the
``springboot-openapi-generator`` skill. It is a plugin module: the framework
discovers it at startup and registers everything listed in ``EVALUATORS``.
"""

from __future__ import annotations

import re

from tasklist_eval.evaluators import Area, GradedEvaluator, PatternSet

# --- Area-presence keywords (does this area appear at all?) ---
SERVER_PRESENCE = PatternSet(
    "server-presence",
    [r"controller|customersapi|/customers|delegate|customerservice"],
)
ADDRESS_PRESENCE = PatternSet("address-client-presence", [r"address"])
ITEM_PRESENCE = PatternSet("item-client-presence", [r"\bitem"])

# --- GENERATED signals (shared across areas) ---
GENERATED = PatternSet(
    "generated",
    [
        r"openapi-generator",
        r"generated[- ]sources",
        r"target/generated-sources",
        re.compile(r"\w*ApiDelegate\b"),  # case-SENSITIVE: implement/read a *ApiDelegate
        r"generated\b.*\binterface|interface\b.*\bgenerated",
        r"webclient\s+execution|webclient\)",
        r"delegate\b.*\bgenerated|generated\b.*\bdelegate",
    ],
)

# --- HANDCODED signals for the server area ---
SERVER_HANDCODED = PatternSet(
    "server-handcoded",
    [
        r"@RestController",
        r"create\s+.*controller",
        r"customercontroller",
        r"@GetMapping|@PostMapping|@RequestMapping",
        r"implement\s+customerservice|create\s+.*customerservice",
        r"lombok",  # hand-written model classes
    ],
)

# --- HANDCODED signals for client areas ---
CLIENT_HANDCODED = PatternSet(
    "client-handcoded",
    [
        r"serviceclient\b.*@component|@component.*serviceclient",
        r"inject.*webclient|webclient via constructor|injected\s+webclient",
        r"mockwebserver",
        r"implement\s+\w*serviceclient",
        r"create\s+`?[\w.]*serviceclient",
    ],
)

AREAS = [
    Area("server", SERVER_PRESENCE, success=[GENERATED], failure=[SERVER_HANDCODED]),
    Area("address-client", ADDRESS_PRESENCE, success=[GENERATED], failure=[CLIENT_HANDCODED]),
    Area("item-client", ITEM_PRESENCE, success=[GENERATED], failure=[CLIENT_HANDCODED]),
]


class GeneratedCodeUsageEvaluator(GradedEvaluator):
    """Grade the fraction of in-scope areas that consume generated code."""

    def __init__(self) -> None:
        super().__init__(
            id="generated-code-usage",
            description=(
                "Graded fraction of in-scope areas (server/address-client/item-client) "
                "that consume generated code rather than being hand-written."
            ),
            areas=AREAS,
            success_label="generated",
            failure_label="handcoded",
            conflict_winner="success",
            unmatched_present="failure",
        )


EVALUATORS = [GeneratedCodeUsageEvaluator()]
