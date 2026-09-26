"""tasklist-eval — evaluate a Kiro spec-driven tasklist for skill success.

This package judges whether the springboot-openapi-generator skill "worked"
using only signals detectable in a ``tasks.md`` file (much cheaper than
generating and inspecting full code). Task completion state (checkbox markers)
is parsed but deliberately ignored when computing verdicts.
"""

from __future__ import annotations

__all__ = ["__version__"]

__version__ = "0.1.0"
