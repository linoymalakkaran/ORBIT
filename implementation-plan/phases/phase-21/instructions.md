# Instructions — Phase 21: Pilot Project Onboarding

> Add this file to your IDE's custom instructions during the first pilot onboarding.

---

## Context

You are onboarding the **first pilot project** onto the AD Ports AI Portal. The pilot is the Dangerous Goods Declaration (DGD) service, owned by the Ports Operations domain team. This phase validates the end-to-end Portal flow with a real project and real users — it is not a test; it is production-readiness validation.

---

## Pilot Project: DGD (Dangerous Goods Declarations)

```
Project ID:      dgd-pilot-001
Domain:          ports-operations
Service Name:    dangerous-goods-declaration
Git Repo:        gitlab.adports.ae/ports-ops/dangerous-goods-declaration
Squad:           Ports Operations Dev Team (6 developers, 1 architect, 1 BA)
Environment:     dev → staging → prod
Keycloak Realm:  adports-dgd
Tier:            pilot (AED 183/month budget)
```

## Pilot Onboarding Checklist

### Week 1 — Infrastructure Setup
- [ ] Project registered in Portal (Portal admin performs)
- [ ] Keycloak realm `adports-dgd` provisioned (via Keycloak MCP)
- [ ] OpenFGA project namespace created with DGD roles
- [ ] AKS namespace `ai-portal-dgd` created with NetworkPolicy
- [ ] Vault project path `/secret/ai-portal/dgd-pilot-001/` configured
- [ ] Pipeline Ledger stream `ledger-dgd-pilot-001` initialized
- [ ] ArgoCD Application manifests created (dev + staging)
- [ ] IDE configuration sent to all 8 team members

### Week 2 — BRD Processing & Planning
- [ ] DGD BRD uploaded to Portal (PDF)
- [ ] `brd-parser` prompt runs → produces intent document
- [ ] Architect reviews + approves intent
- [ ] `architecture-proposal` prompt runs → produces service architecture
- [ ] `work-package-decomposer` runs → produces 8 work packages
- [ ] `story-generator` runs → produces 32 user stories in Jira
- [ ] Sprint planning meeting held with DGD team

### Week 3-4 — Generation Run
- [ ] Backend Agent runs: generates DGD .NET 9 CQRS service
- [ ] Frontend Agent runs: generates DGD Angular micro-frontend
- [ ] DevOps Agent runs: generates CI/CD pipeline + Helm chart
- [ ] QA Agent runs: generates Playwright E2E + Newman tests
- [ ] Human review of all generated artefacts (architect sign-off required)
- [ ] Pipeline runs green end-to-end

### Week 5 — Feedback Collection
- [ ] 3 developers complete portal feedback survey
- [ ] Architect completes architecture review feedback
- [ ] BA completes story quality review
- [ ] All feedback collated into improvement tickets

## Go/No-Go Criteria for Full Rollout

| Criterion | Target |
|-----------|--------|
| Pipeline build success rate | ≥ 90% on first attempt |
| Code review approval rate | ≥ 80% without major changes |
| Playwright E2E pass rate | ≥ 95% |
| Team NPS score | ≥ 40 |
| Hook Engine false-positive rate | ≤ 5% |
| Pilot budget overage | 0 (must stay within AED 183/month) |

## Forbidden Actions During Pilot

| Action | Reason |
|--------|--------|
| Deploying to production without architect approval | Pilot policy |
| Skipping feedback survey | Feedback drives Phase 22+ improvements |
| Using premium LLM tier for all tasks | Pilot budget constraint — use economy for bulk generation |
| Making manual edits to generated code without recording reason | Feedback data collection |

---

*Instructions — Phase 21 — AD Ports AI Portal — Applies to: All Squads (Pilot)*
