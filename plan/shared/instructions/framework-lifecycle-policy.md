# Framework Lifecycle Policy

## Purpose

Defines the mandatory upgrade cadence for all AD Ports software frameworks. Prevents technical debt accumulation and ensures security patches are applied promptly. Enforced automatically by the Fleet Upgrade Agent (Phase 24).

---

## Lifecycle Tiers

| Framework | Current Stable | Minimum Allowed | Block Threshold |
|-----------|---------------|----------------|----------------|
| Angular | 21.x | 20.x (1 major behind) | 18.x or older |
| .NET | 10.x | 9.x (1 major behind, LTS) | 7.x or older |
| Node.js | 22.x (LTS) | 20.x (1 major behind) | 18.x or older |
| Python | 3.13.x | 3.11.x | 3.9.x or older |
| keycloak-js | 25.x | 24.x | 22.x or older |

*Table updated quarterly by the Platform Squad.*

---

## Rules

### Rule 1: Maximum Lag = 1 Major Version

No production service may run a framework more than **1 major version** behind the current stable release.

- **Allowed**: Angular 20 (current = 21, lag = 1)
- **Alert**: Angular 19 (lag = 2) → Fleet Upgrade Agent creates work package
- **Block**: Angular 18 (lag = 3) → New features blocked for this service until upgraded

### Rule 2: 90-Day Upgrade Window

When a new major version is released, all services have **90 calendar days** to upgrade.

- Day 1–30: Informational alert in Portal dashboard.
- Day 31–60: Work package created automatically (P2 priority).
- Day 61–90: Work package escalated to P1; squad lead notified weekly.
- Day 91+: New feature deployments **blocked** for the non-compliant service.

### Rule 3: LTS Preference for .NET

For .NET, **LTS releases are preferred**. Non-LTS versions (.NET 9, .NET 11) are supported for 18 months. LTS versions (.NET 8, .NET 10) are supported for 3 years.

- Services may stay on .NET 9 until .NET 10 LTS is released, then the 90-day window starts.

### Rule 4: Security Patch Lag = 0

Security patches (e.g., `npm audit fix`, `dotnet sdk patch`) must be applied within:
- **CRITICAL CVE**: 72 hours
- **HIGH CVE**: 7 calendar days
- **MEDIUM CVE**: Next sprint

The Vulnerability Radar (Phase 23) enforces this automatically.

---

## Upgrade Process

```
1. Fleet Upgrade Agent reads current versions from Project Registry
2. Fleet Upgrade Agent reads latest stable versions from package managers
3. For each service exceeding lag threshold:
   a. Fleet Upgrade Agent analyses breaking changes
   b. Fleet Upgrade Agent generates upgrade patch
   c. Fleet Upgrade Agent runs tests locally (in sandbox)
   d. Fleet Upgrade Agent opens PR with upgrade patch + rollback plan
   e. PR Review Agent scores the upgrade PR
   f. Engineer reviews and merges
4. After merge, Registry AKS sync updates framework version
5. Compliance automatically restored
```

---

## Exceptions

Exceptions to this policy require:
1. Written justification from squad lead.
2. Platform Squad approval.
3. Time-bounded waiver (max 60 additional days).
4. Recorded in Pipeline Ledger as a policy exception event.

No permanent exceptions are allowed.

---

## Framework Version Sources

The Fleet Upgrade Agent polls these sources weekly:

| Framework | Version Source |
|-----------|---------------|
| Angular | `npm info @angular/core version` |
| .NET | https://dotnetcli.blob.core.windows.net/dotnet/release-metadata/releases-index.json |
| Node.js | https://nodejs.org/en/download/releases.json |
| Python | https://endoflife.date/python.json |
| keycloak-js | `npm info keycloak-js version` |

---

*shared/instructions/framework-lifecycle-policy.md — AI Portal — v1.0*
