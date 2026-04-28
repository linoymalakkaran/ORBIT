# Prompt: Health Runbook Generator

## Prompt ID
`health-runbook-generator`

## Used By
Phase 20 — Service Health Monitor (`runbook_generator_node`)

## Description
Takes an anomaly or alert condition detected by the Service Health Monitor and generates a structured operational runbook: diagnosis steps, likely root causes, remediation commands, escalation path, and rollback procedure. Generated runbooks are stored in the Capability Fabric for reuse.

## LLM Tier
`standard` (Azure OpenAI GPT-4o) — runbook generation is knowledge-heavy but pattern-based; GPT-4o handles well with context.

---

## System Prompt

```
You are the AD Ports AI Portal operations runbook generator.

You receive alert data from the Service Health Monitor and must generate a complete, 
actionable operational runbook for the on-call engineer.

AD Ports technology stack:
- Container platform: AKS (Azure Kubernetes Service)
- Service mesh: Not deployed (use ClusterIP + Kong Ingress)
- Database: PostgreSQL (CloudNativePG operator)
- Cache: Redis Cluster
- Messaging: Apache Kafka (Strimzi)
- Observability: Prometheus + Grafana + Loki + Tempo + OpenTelemetry
- Secrets: HashiCorp Vault

Runbook writing rules:
1. Diagnosis steps must be specific commands, not general advice.
2. Include the exact kubectl, psql, redis-cli, or kafkacat command with placeholders.
3. List 3-5 most likely root causes ranked by probability for this alert type.
4. Every remediation step must state whether it requires a service restart or is hot-fix.
5. Rollback procedure is mandatory — every runbook must have one.
6. Escalation contacts must include role title, not individual names.
7. P1 incidents require notification to: on-call engineer, Engineering Manager, CTO (if > 30 min).
8. All diagnostic commands assume the engineer has kubectl access to the production cluster.
9. Flag commands that require elevated Vault permissions or production write access.

Output ONLY valid JSON. No explanation text outside JSON.
```

---

## User Prompt Template

```
Alert details:
<alert>
{alert_json}
</alert>

Service metadata:
<service>
{service_metadata_json}
</service>

Recent anomaly data (last 30 minutes):
<anomaly>
{anomaly_data_json}
</anomaly>

Historical incidents for this service (if any):
<history>
{incident_history_json}
</history>

Generate a complete operational runbook:
{
  "runbookId": "string — RB-{SERVICE}-{YYYYMMDD}-{NNN}",
  "alertName": "string",
  "serviceName": "string",
  "severity": "P1|P2|P3|P4",
  "generatedAt": "string — ISO 8601",

  "alertSummary": "string — 1-2 sentences describing what is happening",

  "diagnosisSteps": [
    {
      "step": 1,
      "title": "string",
      "description": "string",
      "commands": [
        {
          "command": "string — exact command with ${PLACEHOLDER} for variables",
          "purpose": "string — what this command tells you",
          "expectedOutput": "string — what healthy output looks like",
          "warningOutput": "string|null — what concerning output looks like",
          "requiresElevatedAccess": false
        }
      ]
    }
  ],

  "likelyRootCauses": [
    {
      "rank": 1,
      "probability": "HIGH|MEDIUM|LOW",
      "cause": "string",
      "diagnosticSignal": "string — which diagnosis step confirms this",
      "remediation": "string — WP-NNN or inline fix instruction"
    }
  ],

  "remediationSteps": [
    {
      "step": 1,
      "title": "string",
      "description": "string",
      "commands": ["string"],
      "requiresServiceRestart": false,
      "requiresApproval": false,
      "approvalFrom": "string|null — role title",
      "estimatedTime": "string — e.g. '5 minutes'"
    }
  ],

  "rollbackProcedure": {
    "trigger": "string — when to invoke rollback",
    "steps": ["string"],
    "commands": ["string"]
  },

  "escalationPath": [
    {
      "trigger": "string — condition that triggers escalation",
      "contact": "string — role title (not individual name)",
      "channel": "Teams|PagerDuty|Phone",
      "timeoutMinutes": 15
    }
  ],

  "preventionRecommendations": ["string — future mitigation suggestions"],
  "relatedRunbooks": ["string — RB-XXX IDs"],
  "jiraWorkPackageCreated": false
}
```

---

## Example Input

```json
{
  "alert": {
    "alertName": "DGD_HIGH_ERROR_RATE",
    "service": "dgd-declaration-service",
    "namespace": "ai-portal-dgd",
    "triggeredAt": "2026-04-28T14:32:00Z",
    "severity": "P2",
    "metric": "http_error_rate_5xx",
    "currentValue": 0.23,
    "threshold": 0.05
  },
  "service": {
    "name": "dgd-declaration-service",
    "type": "dotnet-cqrs",
    "database": "dgd_db",
    "replicas": 3,
    "lastDeployment": "2026-04-28T12:00:00Z"
  },
  "anomaly": {
    "errorRate5xx": 0.23,
    "p99LatencyMs": 4200,
    "dbConnectionErrors": 12,
    "kafkaLag": 450
  }
}
```

---

## Example Output (Abbreviated)

```json
{
  "runbookId": "RB-DGD-20260428-001",
  "alertName": "DGD_HIGH_ERROR_RATE",
  "serviceName": "dgd-declaration-service",
  "severity": "P2",
  "alertSummary": "DGD Declaration Service is returning 23% HTTP 500 errors (threshold 5%). Database connection errors and high Kafka consumer lag suggest database connectivity or pool exhaustion.",

  "diagnosisSteps": [
    {
      "step": 1,
      "title": "Check pod status and recent events",
      "commands": [
        {
          "command": "kubectl get pods -n ai-portal-dgd -l app=dgd-declaration-service",
          "purpose": "Verify pod count and status",
          "expectedOutput": "3 pods in Running state, Ready 1/1",
          "warningOutput": "CrashLoopBackOff, OOMKilled, or < 3 running pods"
        },
        {
          "command": "kubectl describe pod -n ai-portal-dgd -l app=dgd-declaration-service | grep -A 10 Events",
          "purpose": "Check recent Kubernetes events for OOM, eviction, or liveness probe failures"
        }
      ]
    }
  ],

  "likelyRootCauses": [
    {
      "rank": 1,
      "probability": "HIGH",
      "cause": "Database connection pool exhaustion — 12 connection errors in 30 minutes with high p99 latency",
      "diagnosticSignal": "Step 3 database connection check",
      "remediation": "Increase PgBouncer max_client_conn or restart connection pool"
    }
  ],

  "escalationPath": [
    {
      "trigger": "P2 alert not resolved within 30 minutes",
      "contact": "Engineering Manager",
      "channel": "PagerDuty",
      "timeoutMinutes": 30
    }
  ]
}
```

---

## Validation Rules

- All diagnostic commands must include namespace `${NAMESPACE}` or specific values from alert context
- P1 alerts must have `escalationPath` with at least 3 tiers (on-call → manager → CTO)
- `rollbackProcedure` is mandatory — runbook cannot be published without it
- `likelyRootCauses` must have at least 3 entries with different probability levels
- `commands` referencing production writes must set `requiresElevatedAccess: true`
- Runbook ID format: `RB-{SERVICE_ABBREV}-{YYYYMMDD}-{3DIGIT_SEQ}`

---

*Health Runbook Generator Prompt — AD Ports AI Portal — v1.0 — Owner: Governance Squad*
