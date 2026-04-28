# Success Metrics & KPIs

## Measurement Philosophy

Every KPI is baselined at the start of Phase 1 from the current state of AD Ports engineering operations. Targets are set relative to baseline during Gate planning. Trends matter as much as point-in-time values.

---

## Phase-Gated KPI Targets

### Gate 1 KPIs (end of Phase 15 — Foundation)

| KPI | Baseline | Target | Measurement Method |
|-----|---------|--------|-------------------|
| Median project bootstrap time (BRD to first deployed scaffold) | ~6 weeks | ≤2 days | Portal event timestamps |
| Orchestrator first-attempt success rate (golden projects) | 0% | ≥75% | Evaluation harness |
| Pipeline Ledger completeness (stages recorded with hashes) | 0% | 100% | Ledger audit query |
| Shared project context functional across 2+ users | No | Yes | Integration test |
| Build + test + security scan pass rate on generated scaffolds | 0% | ≥90% | CI/CD pipeline results |
| Time from approved architecture to repo + pipeline created | Manual (days) | ≤30 min | Portal timestamps |

### Gate 2 KPIs (end of Phase 20 — Ecosystem & Workflow)

| KPI | Baseline | Target | Measurement Method |
|-----|---------|--------|-------------------|
| % of new projects starting via Portal | 0% | ≥30% | Project Registry |
| PR Review Agent agreement with humans | 0% | ≥85% | Human-review calibration sample |
| Service Health Monitor coverage (pilot projects) | 0% | 100% | Health Monitor inventory |
| BA story quality score (accepted without rewrite) | N/A | ≥70% | BA review outcomes |
| Ecosystem agents available | 0 | ≥5 (MPay, Keycloak, CRM, Notification, MDM) | Fabric registry |
| False-reject rate on PR gate (advisory mode) | N/A | ≤5% | PR review outcomes |
| Mean time to CVE remediation | >30 days | ≤7 days | Vulnerability Radar timestamps |
| Integration-test pass rate across environments | 0% (not automated) | ≥80% | Newman reports |
| Service Health Monitor alert-to-real-incident ratio | N/A | ≤2:1 | Alert + incident correlation |

### Gate 3 KPIs (end of Phase 24 — Intelligence & Fleet)

| KPI | Baseline | Target | Measurement Method |
|-----|---------|--------|-------------------|
| % of new projects starting via Portal | ≥30% | ≥65% | Project Registry |
| Ticket Implementation Agent PR merge rate | 0% | ≥60% | Jira + GitHub metrics |
| Framework migration cycle time | 6–12 months | ≤4 weeks per project | Fleet campaign timestamps |
| % of portfolio on preferred framework versions | ~30% | ≥70% | Project Registry stack fingerprints |
| Fleet campaign success rate (projects upgraded / in scope) | N/A | ≥90% | Fleet campaign dashboard |
| Median time from security-patch-ready to 100% fleet coverage | >60 days | ≤5 days | Vulnerability Radar + Fleet |
| QA automation coverage of acceptance criteria | <20% | ≥70% | Test suite analysis |
| Developer NPS for Portal experience | N/A | ≥40 | Quarterly survey |

### Gate 4 KPIs (end of Phase 25 — Scale & Sovereignty)

| KPI | Baseline | Target | Measurement Method |
|-----|---------|--------|-------------------|
| % of new projects starting via Portal | ≥65% | ≥85% | Project Registry |
| Legacy components migrated via Portal | 0 | ≥10 components | Migration Mode registry |
| Compliance evidence preparation time | 1–2 weeks | ≤2 hours | Audit timing |
| External audit passed (SOC-2 Type I or NESA) | N/A | Pass | Audit report |
| Ecosystem agents available | ≥5 | ≥10 | Fabric registry |
| Cross-project component reuse rate | 0% | ≥20% | Registry reuse queries |
| Sovereign deployment available | No | Yes | Deployment verification |

---

## Continuous KPIs (Tracked Throughout All Phases)

| KPI | Direction | What It Measures | Dashboard |
|-----|-----------|----------------|-----------|
| Orchestrator first-attempt success rate | ↑ | Golden-project pass rate per release | Evaluation harness |
| Skills / specs / instructions in library | ↑ | Fabric depth | Portal admin |
| Pipeline Ledger queries per week | ↑ | Governance surface adoption | Ledger analytics |
| LLM cost per orchestration cycle | ↓ | Cost efficiency | LiteLLM + LangSmith |
| Agent error rate | ↓ | Reliability | OpenTelemetry |
| Hook Engine firing rate (pre-hooks blocking) | Stable | Policy enforcement signal | Hook audit log |
| Emergency override count | ↓ | Discipline in governance | Ledger |
| Skill library review compliance (% reviewed on cadence) | ↑ | Standards freshness | Portal admin |

---

## Measurement Infrastructure

All KPIs are backed by durable data sources:

- **Portal event timestamps** → Postgres metadata DB.
- **Evaluation harness** → Automated runs on each release against golden-project corpus.
- **Pipeline Ledger** → EventStoreDB + Postgres index, queryable via Ledger Explorer UI.
- **Project Registry** → Stack fingerprint queries via Registry API.
- **LangSmith** → LLM traces, token counts, cost per run.
- **Prometheus + Grafana** → Infrastructure metrics, service health, pipeline durations.
- **CI/CD results** → GitLab / Azure DevOps API aggregated by the Portal.

---

## Reporting Cadence

| Report | Frequency | Audience | Owner |
|--------|-----------|---------|-------|
| Sprint KPI delta | Every 2 weeks | Squad leads | Delivery Lead |
| Phase progress vs. targets | Monthly | Product Owner, Technical Lead | Delivery Lead |
| Gate readiness dashboard | 2 weeks before Gate | All stakeholders | Technical Lead |
| Portfolio health digest | Weekly | Platform Engineering, Leadership | Platform Lead |
| Vulnerability + obsolescence digest | Weekly | Security Owner, Tech Leads | Security Engineer |
| Developer NPS survey | Quarterly | Leadership | Delivery Lead |

---

*Success Metrics — AI Portal — v1.0 — April 2026*
