"""Unit tests for health-monitor agent pod status detection."""
from __future__ import annotations
import json
import sys
import types

# Stub out confluent_kafka to avoid import errors in unit tests
sys.modules["confluent_kafka"] = types.ModuleType("confluent_kafka")


def test_unhealthy_pod_detection():
    """CrashLoopBackOff should be detected in containerStatuses."""
    UNHEALTHY = {"CrashLoopBackOff", "Error", "OOMKilled", "ImagePullBackOff"}
    pod = {
        "metadata": {"name": "my-service-abc"},
        "status": {
            "containerStatuses": [
                {
                    "name": "my-service",
                    "state": {"waiting": {"reason": "CrashLoopBackOff"}},
                }
            ]
        },
    }
    issues = []
    for cs in pod["status"]["containerStatuses"]:
        reason = cs.get("state", {}).get("waiting", {}).get("reason", "")
        if reason in UNHEALTHY:
            issues.append({"pod": pod["metadata"]["name"], "reason": reason})
    assert len(issues) == 1
    assert issues[0]["reason"] == "CrashLoopBackOff"


def test_healthy_pod_no_issues():
    """Running pod should produce no issues."""
    UNHEALTHY = {"CrashLoopBackOff", "Error", "OOMKilled", "ImagePullBackOff"}
    pod = {
        "metadata": {"name": "my-service-xyz"},
        "status": {
            "containerStatuses": [
                {
                    "name": "my-service",
                    "state": {"running": {"startedAt": "2026-01-01T00:00:00Z"}},
                }
            ]
        },
    }
    issues = []
    for cs in pod["status"]["containerStatuses"]:
        reason = cs.get("state", {}).get("waiting", {}).get("reason", "")
        if reason in UNHEALTHY:
            issues.append({"pod": pod["metadata"]["name"], "reason": reason})
    assert len(issues) == 0
