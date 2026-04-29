---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend", "devops"]
---

# Framework Lifecycle Policy

## Policy Overview

The Fleet Upgrade Agent enforces this policy automatically for all registered services.
Architects and DevOps engineers must comply when creating new services.

## Framework Version Tiers

| Tier | Definition | Action Required |
|---|---|---|
| **CURRENT** | Within 0 major versions of latest | None — continue using |
| **ALERT** | 1 major version behind latest | Upgrade planning required within 60 days |
| **BLOCK** | 2+ major versions behind latest | New deployments BLOCKED; existing services get 30-day exception |
| **EOL** | Vendor end-of-life declared | Emergency upgrade; production deployment blocked immediately |

## Current Supported Versions (as of 2026-04)

| Framework | Latest | ALERT at | BLOCK at |
|---|---|---|---|
| Angular | 20.x | 19.x | 18.x and below |
| .NET | 9.x | 8.x | 7.x and below |
| Node.js | 22.x (LTS) | 20.x | 18.x and below |
| Python | 3.12.x | 3.11.x | 3.10.x and below |
| Java | 21 (LTS) | 17 | 11 and below |

## Upgrade Campaign Process

1. Fleet Upgrade Agent detects version gap (daily scan)
2. Agent creates upgrade work package → Orchestrator
3. Ticket Agent generates feature branch + PR with upgrade changes
4. PR Review Agent validates breaking changes before merge
5. Architect review required for BLOCK-tier upgrades

## Gate 3 Upgrade Checklist

Before any framework upgrade PR can merge:

- [ ] All unit tests pass
- [ ] Integration tests pass
- [ ] Trivy scan: zero CRITICAL CVEs after upgrade
- [ ] SonarQube gate: green
- [ ] Breaking change analysis reviewed by architect
- [ ] Changelog entry added to `CHANGELOG.md`
- [ ] Dependency lockfile updated (`package-lock.json`, `packages.lock.json`, etc.)

## Exceptions Process

Exceptions to BLOCK-tier policy must be:
1. Approved by Platform Architect in writing
2. Recorded in the Service Registry with expiry date (max 90 days)
3. Reviewed monthly by the Platform Team

## Enforcement

- The Fleet Upgrade Agent sets a `lifecycle_status` label on each service in the Project Registry
- Services with `lifecycle_status: BLOCK` cannot receive new ArgoCD deployments (enforced by OPA admission controller)
- The PR Review Agent checks `framework-lifecycle-policy.md` during code review and flags violations

## LTS Strategy

- Only use LTS versions for production services
- Preview/RC versions are allowed in sandbox environments only
- LTS version selection: Node.js even-numbered releases; .NET non-preview; Angular long-term support schedule
