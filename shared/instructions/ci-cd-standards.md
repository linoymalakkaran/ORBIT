---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["devops"]
---

# CI/CD Standards

## Pipeline Structure (GitLab CI)

All services must have the following stages in `.gitlab-ci.yml`:

```
stages:
  - lint
  - test
  - security-scan
  - build
  - trivy-scan
  - deploy-dev
  - deploy-prod
```

## Stage Definitions

### lint
- `.NET`: `dotnet format --verify-no-changes`
- `Angular`: `nx run <app>:lint`
- `Python`: `ruff check .`
- Fail the pipeline on any lint error — warnings are errors in CI

### test
- Run full unit + integration test suite
- Publish test results as JUnit XML (`--logger "junit;LogFilePath=..."`)
- Upload coverage to SonarQube (`sonar-scanner`)
- Quality gate: pipeline fails if SonarQube gate fails

### security-scan
- **GitLeaks**: `gitleaks detect --source . --exit-code 1` — fail on any secret detected
- **Checkmarx SAST**: trigger scan via Checkmarx MCP; fail on CRITICAL findings
- **OWASP Dependency Check**: fail on CVSS ≥ 9.0

### build
- Docker build: `docker build -t harbor.ai.adports.ae/orbit/<service>:<tag> .`
- Tag strategy: `<git-sha>` for feature branches, `latest` + `v<semver>` for main
- Push to Harbor on main branch only

### trivy-scan
- `trivy image --exit-code 1 --severity CRITICAL harbor.ai.adports.ae/orbit/<service>:<tag>`
- Fail on CRITICAL CVEs; HIGHS generate warnings only

### deploy-dev
- `helm upgrade --install <service> charts/<service> -n ai-portal-dev -f values/dev.yaml`
- `--wait --timeout 3m`
- Run smoke test: `curl -sf https://api-dev.ai.adports.ae/api/v1/<service>/health/live`
- Only on `main` branch or `release/*` branches

### deploy-prod
- Manual trigger only (`when: manual`)
- Uses ArgoCD sync: `argocd app sync <service> --prune --timeout 120`
- Requires approval from 2 reviewers (GitLab approval rules)
- Notification to Teams channel on success/failure

## Branch Strategy

- `main` → production; protected; requires 2 approvals + passing pipeline
- `develop` → integration; auto-deploys to dev environment
- `feature/<ticket-id>-description` → feature branches; no direct push to main
- `release/<version>` → release branches; hotfixes cherry-picked from main

## Image Tagging

```
harbor.ai.adports.ae/orbit/<service>:<git-sha>   # always
harbor.ai.adports.ae/orbit/<service>:latest      # main branch only
harbor.ai.adports.ae/orbit/<service>:v1.2.3      # tags only
```

## Commit Convention (Conventional Commits)

```
feat(<scope>): short description
fix(<scope>): short description
docs(<scope>): short description
chore(<scope>): short description
```

`scope` = service name (e.g. `portal-api`, `orchestrator`, `gap-G01`)
