# Instructions — Phase 23: Vulnerability Remediation Agent

> Add this file to your IDE's custom instructions when working on the Vulnerability Remediation Agent or CVE triage workflows.

---

## Context

You are building the **AD Ports Vulnerability Remediation Agent** — an autonomous agent that monitors the AD Ports service fleet for security vulnerabilities (CVEs from Snyk/Trivy, SAST findings from Checkmarx, exposed secrets from git history), triages them by urgency, and initiates appropriate remediation actions ranging from automated dependency updates to emergency secret rotation.

---

## Vulnerability Urgency Tiers

```python
class VulnUrgency(str, Enum):
    IMMEDIATE  = "IMMEDIATE"   # Remediate within 4 hours
    URGENT     = "URGENT"      # Remediate within 24 hours
    STANDARD   = "STANDARD"    # Remediate within 7 days
    DEFERRED   = "DEFERRED"    # Remediate in next planned sprint

# Classification logic
def classify_urgency(vuln: Vulnerability) -> VulnUrgency:
    # Secrets ALWAYS immediate — regardless of CVSS
    if vuln.finding_type == "exposed_secret":
        return VulnUrgency.IMMEDIATE

    if vuln.cvss_score >= 9.0 and vuln.asset_criticality == "CRITICAL":
        return VulnUrgency.IMMEDIATE
    if vuln.cvss_score >= 7.0:
        return VulnUrgency.URGENT
    if vuln.cvss_score >= 4.0:
        return VulnUrgency.STANDARD
    return VulnUrgency.DEFERRED
```

## Remediation Action Decision Tree

```
Finding received
    │
    ├── exposed_secret?
    │       └── YES → SecretRotationWorkflow (Temporal, immediate)
    │
    ├── CVSS ≥ 7.0 (HIGH/CRITICAL)?
    │       ├── Single service → create_urgent_patch_pr
    │       └── Multiple services → FleetUpgradeCampaignWorkflow
    │
    ├── CVSS 4.0-6.9 (MEDIUM)?
    │       └── Create Jira ticket (STANDARD urgency, next sprint)
    │
    ├── CVSS < 4.0 (LOW/INFO)?
    │       └── Create Jira ticket (DEFERRED, backlog)
    │
    └── SAST finding?
            ├── Injection / AuthZ → URGENT PR fix
            └── Code quality → STANDARD Jira ticket
```

## Secret Rotation Workflow

```python
@workflow.defn
class SecretRotationWorkflow:
    """Emergency secret rotation — completes within 4 hours."""

    @workflow.run
    async def run(self, params: SecretRotationParams) -> RotationResult:
        # Step 1: Rotate in source system (Azure Key Vault / DB / API provider)
        new_value = await workflow.execute_activity(
            rotate_secret_in_source_system,
            args=[params.secret_type, params.service_name],
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=STANDARD_RETRY_POLICY,
        )

        # Step 2: Update Vault (agents read from here)
        await workflow.execute_activity(
            update_vault_secret,
            args=[params.vault_path, new_value],
            start_to_close_timeout=timedelta(minutes=10),
        )

        # Step 3: Rolling restart affected pods (pick up new secret)
        await workflow.execute_activity(
            rolling_restart_deployment,
            args=[params.service_name, params.namespace],
            start_to_close_timeout=timedelta(minutes=20),
        )

        # Step 4: Remove old secret from git history (if exposed in commit)
        if params.exposed_in_git:
            await workflow.execute_activity(
                remove_secret_from_git_history,
                args=[params.repo_url, params.leaked_commit_sha],
                start_to_close_timeout=timedelta(minutes=60),
            )

        # Step 5: Create incident ticket + notify
        await workflow.execute_activity(
            create_security_incident_ticket,
            args=[params, "secret_rotation_completed"],
        )

        return RotationResult(success=True, rotated_at=datetime.utcnow())
```

## Notification Templates

```python
# IMMEDIATE / URGENT — PagerDuty + Slack
URGENT_NOTIFICATION = """
🔴 SECURITY ALERT — {urgency}

Vulnerability: {cve_id or finding_id}
Service:       {service_name}
CVSS Score:    {cvss_score}
Description:   {description}
Remediation:   {action_taken}
Deadline:      {remediation_deadline}

Ledger Event:  {ledger_event_id}
Runbook:       {runbook_url}
"""

# STANDARD — Slack only
STANDARD_NOTIFICATION = """
⚠️  Security Finding — {urgency}

{cve_id}: {summary}
Affected: {service_count} service(s)
Jira Ticket: {jira_url}
Expected Fix Sprint: {sprint_name}
"""
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Closing a CRITICAL CVE without fix verification | Verification (CI pipeline pass) is mandatory |
| Delaying exposed secret rotation | Secrets start 4-hour SLA immediately |
| `git push --force` to `main` | Even for git history cleanup — requires separate branch + PR |
| Suppressing a finding without architect approval | All suppressions recorded in Pipeline Ledger |

---

*Instructions — Phase 23 — AD Ports AI Portal — Applies to: Governance Squad*
