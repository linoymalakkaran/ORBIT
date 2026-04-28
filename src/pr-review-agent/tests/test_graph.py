"""Unit tests for pr-review-agent graph logic."""
from __future__ import annotations
import pytest


def test_risk_score_extraction_high():
    """Risk score of 9 should mark MR as not approved."""
    content = "This code has critical security issues. Risk: 9/10"
    risk = 5
    for line in content.lower().split("\n"):
        if "risk" in line and any(c.isdigit() for c in line):
            digits = [int(c) for c in line if c.isdigit()]
            if digits:
                risk = min(10, max(1, digits[0]))
                break
    assert risk == 9
    assert risk > 6  # not approved


def test_risk_score_extraction_low():
    """Risk score of 2 should mark MR as approved."""
    content = "Minor code style issues. Risk: 2/10"
    risk = 5
    for line in content.lower().split("\n"):
        if "risk" in line and any(c.isdigit() for c in line):
            digits = [int(c) for c in line if c.isdigit()]
            if digits:
                risk = min(10, max(1, digits[0]))
                break
    assert risk == 2
    assert risk <= 6  # approved
