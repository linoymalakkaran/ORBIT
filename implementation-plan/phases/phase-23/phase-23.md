# Phase 23 — Vulnerability Radar

## Summary

Implement the **Vulnerability Radar** — a continuous security intelligence layer that monitors all registered services for newly disclosed CVEs, dependency vulnerabilities (Snyk), SAST findings (SonarQube/Checkmarx), container image vulnerabilities (Trivy), and secrets accidentally committed (GitLeaks). When a critical finding is detected, the Radar auto-creates a remediation work package and assigns it to the owning squad.

---

## Objectives

1. Implement CVE feed ingestion (NVD + GitHub Security Advisories).
2. Implement Snyk dependency vulnerability scanner (scheduled + on-demand).
3. Implement SonarQube findings poller (new CRITICAL/BLOCKER findings).
4. Implement Checkmarx SAST results reader (new HIGH/CRITICAL findings).
5. Implement Trivy container image scanner (all images in ACR).
6. Implement GitLeaks secret scanner (scan all repos on new commit).
7. Implement vulnerability prioritization engine (CVSS + asset criticality).
8. Implement auto-remediation work package creator.
9. Implement Vulnerability Radar dashboard in Portal.
10. Implement `adports-ai security scan` CLI command.

---

## Prerequisites

- Phase 01 (AKS + ACR — images to scan).
- Phase 09 (SonarQube MCP + Checkmarx MCP — to read findings).
- Phase 19 (Project Registry — all registered services + repos).
- Phase 18 (Hook Engine — remediation work packages evaluated against policies).

---

## Duration

**3 weeks**

**Squad:** Governance Squad (1 security engineer + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | CVE feed ingestion | NVD feed ingested; new CVE-2025-XXXXX matched to affected services |
| D2 | Snyk scheduled scan | Weekly Snyk scan of all registered repos; findings stored |
| D3 | SonarQube poller | New CRITICAL finding → alert within 15 minutes |
| D4 | Checkmarx reader | New HIGH/CRITICAL SAST finding → alert + work package |
| D5 | Trivy image scanner | Daily ACR scan; CRITICAL CVE in image → alert |
| D6 | GitLeaks scanner | Secret committed in any registered repo → alert within 5 minutes |
| D7 | Prioritization engine | CVSS score × asset criticality = remediation priority |
| D8 | Auto-remediation WP | P1 finding → Portal work package created and assigned automatically |
| D9 | Vulnerability dashboard | All findings across all services visible with severity and age |
| D10 | CLI command | `adports-ai security scan --project=dgd` runs all scanners |

---

## Vulnerability Prioritization Engine

```python
# vulnerability_radar/prioritizer.py

ASSET_CRITICALITY = {
    "production": 3.0,
    "staging":    1.5,
    "dev":        0.5,
}

SERVICE_CRITICALITY = {
    "payment-service":       3.0,   # Customer payment data
    "identity-service":      3.0,   # Auth infrastructure
    "declaration-service":   2.0,   # Regulatory compliance
    "notification-service":  1.0,   # Non-critical path
}

def calculate_priority(finding: VulnerabilityFinding, service: Service) -> RemediationPriority:
    """
    Priority = CVSS × Asset Criticality × Service Criticality
    CVSS: 0-10 (from NVD/Snyk)
    Asset criticality: 0.5–3.0 (by environment)
    Service criticality: 1.0–3.0 (by service type)
    """
    env_factor = ASSET_CRITICALITY.get(service.primary_environment, 1.0)
    svc_factor = SERVICE_CRITICALITY.get(service.name, 1.0)
    score = finding.cvss_score * env_factor * svc_factor

    if score >= 20:     return RemediationPriority.P0_CRITICAL   # Emergency: fix within 24h
    if score >= 10:     return RemediationPriority.P1_HIGH        # Fix within 1 week
    if score >= 5:      return RemediationPriority.P2_MEDIUM      # Fix in next sprint
    return              RemediationPriority.P3_LOW                # Fix when convenient
```

---

## CVE Feed Ingestion

```python
# vulnerability_radar/cve_feed.py
async def ingest_nvd_feed() -> int:
    """
    Ingests NVD CVE feed and matches against installed packages
    tracked in the Project Registry.
    """
    # Fetch last 7 days of NVD CVEs
    response = await http.get(
        "https://services.nvd.nist.gov/rest/json/cves/2.0",
        params={"pubStartDate": (datetime.utcnow() - timedelta(days=7)).isoformat(), "resultsPerPage": 2000}
    )
    cves = response.json()["vulnerabilities"]

    matched = 0
    for cve in cves:
        # Extract affected package info from CPE
        affected_packages = extract_affected_packages(cve)
        for pkg in affected_packages:
            # Find registered services using this package
            services = await registry_db.find_services_using_package(pkg.name, pkg.version_range)
            for service in services:
                await store_finding(CVEFinding(
                    service_id=service.id,
                    cve_id=cve["cve"]["id"],
                    package=pkg.name,
                    cvss_score=extract_cvss_score(cve),
                    description=cve["cve"]["descriptions"][0]["value"][:500],
                    published_at=cve["cve"]["published"]
                ))
                matched += 1

    return matched
```

---

## GitLeaks Integration

```yaml
# .gitleaks.toml — generated for every project repo
[extend]
useDefault = true

[[rules]]
description = "AD Ports JWT tokens"
id = "adports-jwt"
regex = '''eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9\.[A-Za-z0-9+/=]+\.[A-Za-z0-9+/=]+'''
tags = ["token", "adports"]

[[rules]]
description = "Vault tokens"
id = "vault-token"
regex = '''hvs\.[A-Za-z0-9+/=]{24,}'''
tags = ["vault", "secret"]

[[rules]]
description = "PostgreSQL connection strings with password"
id = "postgres-conn-string"
regex = '''postgres:\/\/[^:]+:[^@]{4,}@'''
tags = ["database", "secret"]
```

The GitLeaks scanner runs on every push via GitLab CI pre-receive hook:

```yaml
# Added to .gitlab-ci.yml by DevOps Agent
gitleaks-scan:
  stage: security-scan
  image: zricethezav/gitleaks:v8
  script:
    - gitleaks detect --source=. --config=.gitleaks.toml --exit-code 1
  allow_failure: false
```

---

## Vulnerability Dashboard

```html
<!-- vulnerability-radar/radar-dashboard.component.ts -->
<div class="radar-layout">
  <!-- Summary cards -->
  <div class="summary-cards grid grid-cols-5 gap-4 mb-6">
    <adports-severity-card [severity]="'CRITICAL'" [count]="summary.critical" />
    <adports-severity-card [severity]="'HIGH'"     [count]="summary.high" />
    <adports-severity-card [severity]="'MEDIUM'"   [count]="summary.medium" />
    <adports-severity-card [severity]="'LOW'"      [count]="summary.low" />
    <adports-severity-card [severity]="'SECRETS'"  [count]="summary.secrets" />
  </div>

  <!-- Findings table with filters -->
  <adports-findings-table
    [findings]="findings()"
    [filters]="filters"
    (createWorkPackage)="onCreateWorkPackage($event)"
    (suppressFinding)="onSuppressFinding($event)"
  />

  <!-- Risk trend chart (last 90 days) -->
  <adports-risk-trend-chart [trendData]="trendData()" />
</div>
```

---

## Step-by-Step Execution Plan

### Week 1: Feed Ingestion + Scanners

- [ ] Implement NVD CVE feed ingestion with package matching.
- [ ] Implement Snyk scheduled scan (weekly + on-demand via MCP).
- [ ] Implement Trivy ACR image scanner (daily scheduled job).
- [ ] Implement GitLeaks scanner integration (CI hook + manual scan).

### Week 2: Prioritization + Auto-Remediation

- [ ] Implement prioritization engine (CVSS × asset × service criticality).
- [ ] Implement SonarQube findings poller (new CRITICAL/BLOCKER within 15 min).
- [ ] Implement Checkmarx SAST results reader.
- [ ] Implement auto-remediation work package creator (P0/P1 findings → Portal WP).
- [ ] Implement notification routing (on-call + security team).

### Week 3: Dashboard + CLI + Integration

- [ ] Implement Vulnerability Radar dashboard.
- [ ] Implement finding suppression flow (with reason + expiry + Ledger record).
- [ ] Implement `adports-ai security scan` CLI command.
- [ ] End-to-end test: introduce known vulnerable package → Snyk detects → WP created → notified.
- [ ] Test: secret committed in DGD repo → GitLeaks detects → alert within 5 minutes.

---

## Gate Criterion (Gate 3 Prerequisite)

- CVE feed ingestion running daily; matches against all registered services.
- Snyk scan finds known vulnerable package and creates P1 work package.
- GitLeaks detects committed secret within 5 minutes of push.
- Trivy scans all images in ACR daily; CRITICAL CVE → alert.
- Vulnerability dashboard shows all findings across all registered projects.
- Zero open P0 vulnerabilities before Gate 3 validation.

---

*Phase 23 — Vulnerability Radar — AI Portal — v1.0*
