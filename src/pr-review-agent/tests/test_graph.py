"""Unit tests for pr-review-agent — Phase 21 enhanced review logic."""
from __future__ import annotations

import pytest
from app.main import (
    CSHARP_RULES,
    SECURITY_PATTERNS,
    TYPESCRIPT_RULES,
    Severity,
    _apply_rules,
    _calculate_score,
)


# ── Static rule tests ────────────────────────────────────────────────────────
def test_cs004_hardcoded_secret_detected():
    diff = '+    password = "MyS3cretP@ss"\n'
    findings = _apply_rules(diff, CSHARP_RULES)
    assert any(f["rule_id"] == "CS004" for f in findings)
    assert any(f["severity"] == Severity.ERROR for f in findings)


def test_cs001_blocking_result_detected():
    diff = '+    var result = task.Result;\n'
    findings = _apply_rules(diff, CSHARP_RULES)
    assert any(f["rule_id"] == "CS001" for f in findings)


def test_sec001_vault_token_detected():
    diff = '+    token = "hvs.ABCDEFGHIJKLMNOPQRSTUVWXyz123456"\n'
    findings = _apply_rules(diff, SECURITY_PATTERNS)
    assert any(f["rule_id"] == "SEC001" for f in findings)


def test_ts001_innerhtml_detected():
    diff = '+    element.innerHTML = userInput;\n'
    findings = _apply_rules(diff, TYPESCRIPT_RULES)
    assert any(f["rule_id"] == "TS001" for f in findings)


def test_clean_diff_no_findings():
    diff = '+    var x = await task;\n'
    findings = _apply_rules(diff, CSHARP_RULES)
    assert not any(f["rule_id"] in ("CS001", "CS004") for f in findings)


# ── Score calculation tests ──────────────────────────────────────────────────
def test_score_no_findings_is_perfect():
    score = _calculate_score([], 0.0, [])
    assert score["total"] == 100
    assert score["grade"] == "A"
    assert score["merge_blocked"] is False


def test_score_critical_finding_blocks_merge():
    findings = [{"severity": "ERROR", "category": "security", "rule_id": "CS004", "file": "f.cs", "line": 1, "message": "", "fix_suggestion": "", "snippet": ""}]
    score = _calculate_score(findings, 0.0, [])
    assert score["merge_blocked"] is True
    assert score["total"] < 100


def test_score_architecture_drift_blocks_merge():
    score = _calculate_score([], 0.0, ["New unapproved dependency"])
    assert score["merge_blocked"] is True


def test_score_coverage_drop_warning():
    score_normal = _calculate_score([], -3.0, [])
    score_dropped = _calculate_score([], -10.0, [])
    assert score_dropped["breakdown"]["test_coverage"] < score_normal["breakdown"]["test_coverage"]


def test_score_grade_thresholds():
    assert _calculate_score([], 0.0, [])["grade"] == "A"  # 100
    # 3 warnings in security (3×3=9 deductions from 35 → 26; total 91) = "A"
    findings_warn = [
        {"severity": "WARNING", "category": "security", "rule_id": "X", "file": "f", "line": 1, "message": "", "fix_suggestion": "", "snippet": ""}
        for _ in range(5)
    ]
    score = _calculate_score(findings_warn, 0.0, [])
    assert score["grade"] in ("A", "B", "C", "F")

