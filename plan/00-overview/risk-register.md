# Risk Register

## Risk Rating Guide

- **Severity:** Critical / High / Medium / Low
- **Probability:** High (>60%) / Medium (30–60%) / Low (<30%)
- **Risk Score:** Severity × Probability → drives mitigation priority

---

## Active Risks

### R01 — Gate 1 Failure: Orchestrator Cannot Produce Reliable Scaffolds

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Probability** | Medium |
| **Risk Score** | Critical-Medium |
| **Phase** | 10, 11, 12 |
| **Owner** | Technical Lead |

**Description:** The Orchestration Agent fails to consistently produce architecture proposals and scaffolds that meet quality standards. Golden-project harness pass rate below 75% at Gate 1 review.

**Mitigation:**
- Walking skeleton sprint in week 1 of Phase 10 to validate core flow end-to-end.
- Evaluation harness with real historical AD Ports BRDs from day 1 of Phase 10.
- Template-first architecture — LLM surface is deliberately small (20–30% of decisions).
- Hard go/no-go gate: if harness pass rate <75%, Phase 11+ deferred until root cause resolved.
- Daily monitoring of harness results from Phase 10 onward.

**Residual Risk After Mitigation:** Low

---

### R02 — Organisational Adoption Resistance

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | High |
| **Risk Score** | High-High |
| **Phase** | All |
| **Owner** | Product Owner + Delivery Lead |

**Description:** Development teams are attached to existing workflows and resist adopting the Portal. Portal usage stays low; investment does not deliver ROI.

**Mitigation:**
- Portal is **additive, never mandatory** in Phases 1–2. Developers can still do things the old way.
- Early-adopter programme with 3–5 willing pilot teams identified before Phase 1.
- Measurable wins published internally after Gate 1 (bootstrap time reduction, quality improvement).
- IDE integration means no context switching — Copilot/Cursor users get portal benefits in their existing tool.
- Quarterly NPS survey; adoption blockers acted on within one sprint.
- "Portal did it" success stories shared at engineering all-hands.

**Residual Risk After Mitigation:** Medium (adoption is always a human behaviour challenge)

---

### R03 — Standards Library Rots

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | High |
| **Risk Score** | High-High |
| **Phase** | 07, ongoing |
| **Owner** | Platform Lead |

**Description:** Skills, specs, and instructions drift from actual AD Ports practices over time. Portal produces outdated scaffolds. Teams stop trusting outputs.

**Mitigation:**
- Skills/specs/instructions owned by Platform Squad as first-class products with named owners.
- Quarterly review cadence enforced by tooling — stale instructions flagged in Portal admin UI.
- PR Review Agent feeds recurring patterns back to skill owners with improvement suggestions.
- Each skill has a `last-reviewed` date; Portal dashboard surfaces overdue reviews.
- Breaking changes in shared services trigger required instruction updates.

**Residual Risk After Mitigation:** Low-Medium

---

### R04 — Ecosystem Agents Drift from Real Systems

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | Medium |
| **Risk Score** | High-Medium |
| **Phase** | 25 |
| **Owner** | Platform Lead (per-agent: respective system team) |

**Description:** Ecosystem agents (MPay, CRM, etc.) become out-of-sync with the actual API contracts and authentication flows of the underlying systems. Generated integrations fail at runtime.

**Mitigation:**
- Each ecosystem agent is **owned by the respective platform team** as a first-class product.
- Semver contract on agent specs — breaking changes trigger required update notifications.
- Automated smoke tests against sandbox environments run on every agent release.
- Agent spec versioning enforced; consuming projects declare the agent version they depend on.

**Residual Risk After Mitigation:** Low

---

### R05 — LLM Cost Blowout

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Probability** | High |
| **Risk Score** | Medium-High |
| **Phase** | 10, ongoing |
| **Owner** | Technical Lead + Finance |

**Description:** Unbounded agent invocations (especially fleet campaigns or deep orchestration cycles) drive LLM API costs to unsustainable levels.

**Mitigation:**
- Per-project LLM budget hooks (Phase 18) hard-cap spend per orchestration cycle.
- Portfolio-level monthly cap with alert threshold at 80% utilisation.
- LiteLLM routes routine tasks to economy models (DeepSeek/Llama).
- Template-first architecture reduces LLM invocations by 70–80%.
- Cost dashboard in LangSmith + Portal Audit view, reviewed weekly.
- Self-hosted Llama 3.3 for high-volume routine tasks from Phase 4.

**Residual Risk After Mitigation:** Low

---

### R06 — Fleet Campaign Breaks Multiple Projects Simultaneously

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Probability** | Medium |
| **Risk Score** | Critical-Medium |
| **Phase** | 24 |
| **Owner** | Intelligence Squad Lead |

**Description:** A fleet upgrade campaign applies a breaking change across many projects; the verification gate fails to catch it; multiple production services degrade simultaneously.

**Mitigation:**
- Wave-based rollout: pilot wave of 2–3 low-risk projects before broad rollout.
- Auto-pause if failure rate in any wave exceeds 20%.
- Per-project verification report must pass before campaign advances to next wave.
- High-risk campaigns (major framework version) require CAB approval + tech lead acknowledgment.
- One-click rollback per project with automatic Helm release revert.
- Production campaigns (Phase 4 only) require additional production-readiness checklist.

**Residual Risk After Mitigation:** Low-Medium

---

### R07 — Service Health Monitor Produces Alert Fatigue

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | Medium |
| **Risk Score** | High-Medium |
| **Phase** | 20 |
| **Owner** | Governance Squad Lead + SRE |

**Description:** Too many alerts (false positives, transient failures, noisy checks) cause on-call teams to ignore notifications, defeating the purpose of health monitoring.

**Mitigation:**
- Severity-tier routing — not every alert pages on-call; most go to Teams channel only.
- Auto-remediation for low-severity common failures (pod restart, cache clear).
- Silencing workflow for planned maintenance windows.
- Alert calibration feedback loop: SRE marks each alert as True/False positive; system learns over time.
- First 2 weeks of monitoring in advisory-only mode before live paging.

**Residual Risk After Mitigation:** Low

---

### R08 — Pipeline Ledger Storage Growth

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Probability** | High |
| **Risk Score** | Medium-High |
| **Phase** | 05 |
| **Owner** | Core Squad Lead |

**Description:** Append-only ledger grows unbounded; storage costs become material; query performance degrades over time.

**Mitigation:**
- Tiered storage: Redis (hot, 7 days), EventStoreDB (warm, 1 year), Azure Blob immutable bucket (cold, indefinite).
- Postgres index compaction on a monthly schedule.
- Retention policy by compliance class: standard (3 years warm), NESA-regulated (7 years warm).
- Storage cost reviewed quarterly; tiering thresholds adjusted as data grows.

**Residual Risk After Mitigation:** Low

---

### R09 — Shared Project Context Leaks Sensitive Data

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Probability** | Medium |
| **Risk Score** | Critical-Medium |
| **Phase** | 06 |
| **Owner** | Core Squad Lead + Security Owner |

**Description:** Sensitive data from one project's AI context (PII, secrets, classified architecture) is visible to team members of another project.

**Mitigation:**
- Scrubbing hooks redact credentials, PII, and classified references at context-capture time (before Redis write).
- OpenFGA fine-grained permissions: team member of Project A cannot see Project B's context without explicit grant.
- Cross-project references require explicit permission grant (default-closed).
- Context access audit log: every cross-project reference is a Pipeline Ledger event.
- Regular penetration testing of context isolation from Phase 2 onward.

**Residual Risk After Mitigation:** Low

---

### R10 — Generated Code Quality Below Human Standard

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | Medium |
| **Risk Score** | High-Medium |
| **Phase** | 12, 13, 14 |
| **Owner** | Delivery Agents Squad Lead |

**Description:** Generated scaffolds contain patterns that don't meet AD Ports coding standards, leading to technical debt or security issues from day one.

**Mitigation:**
- Template-first: 70–80% of generated code from deterministic templates, not LLM.
- Mandatory build + unit test + SAST pass before any scaffold is accepted.
- PR Review Agent reviews all generated code before it reaches human review.
- Evaluation harness validates generated code against AD Ports standards on every release.
- Advisory-mode PR gating in Phase 2 gives teams confidence before enforcement in Phase 3.

**Residual Risk After Mitigation:** Low-Medium

---

### R11 — Scope Creep into a Build-Everything Platform

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | Medium |
| **Risk Score** | High-Medium |
| **Phase** | All |
| **Owner** | Product Owner + Technical Lead |

**Description:** Well-meaning requests to "just add" a custom runtime, a new DSL, a custom IDE, or a proprietary actor framework dilute focus and erode the build-vs-integrate discipline.

**Mitigation:**
- Build-vs-integrate decision table is authoritative and reviewed at each Gate.
- Explicit ban on custom DSL or proprietary runtime written into the project charter.
- Monthly scope reviews by Product Owner; new "build" items require explicit justification.
- Technical Lead has veto on build-vs-integrate violations.

**Residual Risk After Mitigation:** Low

---

### R12 — Data Residency Violations via LLM Egress

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Probability** | Low |
| **Risk Score** | Critical-Low |
| **Phase** | 10 |
| **Owner** | Security Owner |

**Description:** BRD/HLD content containing classified or regulated data is sent to an external LLM provider, violating data residency or data classification requirements.

**Mitigation:**
- Redaction hooks strip UAE-PASS national IDs, MPay merchant secrets, classified references before any LLM call.
- Projects declared as classified automatically route to on-premises self-hosted LLM (available Phase 4).
- Data-residency declaration on every project; redaction hooks check declaration before routing.
- Redaction is a pre-hook: if it fails, the LLM call is blocked, not retried.

**Residual Risk After Mitigation:** Very Low

---

---

### R13 — LLM Provider Outage (External)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | Low |
| **Risk Score** | High-Low |
| **Phase** | 10, ongoing |
| **Owner** | Technical Lead |

**Description:** A primary LLM provider (Anthropic / Azure OpenAI) experiences an extended outage, blocking all Portal operations that require Premium or Standard tier inference.

**Mitigation:**
- LiteLLM automatic provider fallback: Premium (Claude) → Standard (GPT-4o) → Economy (DeepSeek) on `ProviderOutage` error.
- Sovereign tier (vLLM on AKS) is always available and unaffected by cloud provider outages.
- Portal UI surfaces degraded mode banner when fallback is active.
- SLA monitoring with PagerDuty alert if primary provider unavailable > 15 min.
- Monthly DR drill: simulate outage, verify fallback chain routes correctly.

**Residual Risk After Mitigation:** Low

---

### R14 — Compromised Agent Service Account

| Field | Value |
|-------|-------|
| **Severity** | Critical |
| **Probability** | Low |
| **Risk Score** | Critical-Low |
| **Phase** | 08, 09, ongoing |
| **Owner** | Security Owner |

**Description:** An MCP server or Orchestrator service account's Keycloak client secret is compromised, allowing an attacker to call tools with elevated permissions, potentially exfiltrating data or injecting malicious code into generated PRs.

**Mitigation:**
- Service account client secrets rotated every 90 days via Vault automation.
- All MCP tool calls validated by Hook Engine — even if token is valid, policy limits what actions are permitted.
- Pipeline Ledger provides tamper-evident audit trail; anomalous behaviour is detectable.
- MCP servers run with least-privilege AKS service accounts (no cluster-admin).
- Keycloak short-lived tokens (15 min max expiry) for service-to-service calls.
- Anomaly detection: volume of MCP calls per service account alerted on > 2× baseline.

**Residual Risk After Mitigation:** Low

---

### R15 — AKS Version End-of-Life

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Probability** | High |
| **Risk Score** | Medium-High |
| **Phase** | 01, 24, ongoing |
| **Owner** | Infra Squad Lead |

**Description:** AKS 1.30.x reaches end of support. Unpatched Kubernetes clusters expose the Portal to CVEs with no vendor fixes available.

**Mitigation:**
- `framework-lifecycle-policy.md` mandates upgrade within 60 days of a minor version reaching end-of-support.
- Fleet Upgrade Agent (Phase 24) manages AKS node pool upgrades.
- Staging cluster upgraded first; 1-week validation window before production upgrade.
- Azure Advisor alerts enable 90-day advance notice of deprecation.
- AKS upgrade tested in CI via ephemeral clusters on each quarterly release.

**Residual Risk After Mitigation:** Low

---

### R16 — Key Personnel Departure

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Probability** | Medium |
| **Risk Score** | High-Medium |
| **Phase** | All |
| **Owner** | Delivery Lead |

**Description:** Loss of a squad lead or principal engineer during a critical phase delays delivery and causes knowledge loss for complex Orchestrator or Temporal workflow logic.

**Mitigation:**
- Two engineers per critical component at all times (bus factor ≥ 2 enforced by team structure policy).
- Capability Fabric stores all implementation patterns — knowledge is externalised, not in heads.
- Weekly knowledge-transfer sessions recorded and stored in SharePoint.
- Succession plan documented for each squad lead role.
- Onboarding playbook updated every quarter so replacements can ramp in < 2 weeks.

**Residual Risk After Mitigation:** Medium (people risk always partially residual)

---

*Risk Register — AI Portal — v1.0 — April 2026 | Updated: v1.4*  
*Review frequency: Monthly by Technical Lead + Security Owner. Gates trigger a full review.*
