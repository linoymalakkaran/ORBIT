# Phase 15 — DevOps & Infrastructure Agent (Gate 1 Checkpoint)

## Summary

Implement the **DevOps & Infrastructure Agent** — generates complete CI/CD pipelines (GitLab CI or Azure DevOps), Pulumi/Terraform IaC for Azure resources, Helm chart scaffolds, Kong API gateway routes, and security tool configurations (SonarQube, Checkmarx, Snyk, Trivy). This is the **Gate 1 checkpoint** — after this phase, the platform can autonomously generate a deployable, secure application stack for a new project.

---

## Objectives

1. Implement GitLab CI pipeline generator (full: build → test → scan → deploy stages).
2. Implement Azure DevOps pipeline generator (alternative to GitLab CI).
3. Implement Pulumi TypeScript IaC generator for Azure resources.
4. Implement Terraform HCL generator (alternative to Pulumi).
5. Implement Helm chart generator (wraps Phase 12 helm templates into full chart).
6. Implement Kong route + plugin configuration generator.
7. Implement security tool config generators (SonarQube, Checkmarx, Snyk, Trivy).
8. Implement ArgoCD application manifest generator.
9. Implement DevOps Agent end-to-end worker.
10. Conduct Gate 1 validation.

---

## Prerequisites

- Phase 10 (Orchestrator).
- Phase 12 (Backend Agent — Helm chart templates).
- Phase 09 (GitLab MCP + AKS MCP + SonarQube MCP + Checkmarx MCP).
- Phase 01 (ArgoCD deployed in cluster).

---

## Duration

**4 weeks** (last week = Gate 1 validation)

**Squad:** DevOps Squad + Delivery Agents Squad (2 senior DevOps + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | GitLab CI pipeline | All stages pass for DGD service (build → test → scan → deploy-dev) |
| D2 | Azure DevOps pipeline | Same stages pass on ADO for DGD service |
| D3 | Pulumi IaC | `pulumi up` creates Azure resources (PSQL DB, Storage Account, Service Bus) |
| D4 | Helm chart | `helm install --dry-run` validates; `helm install` deploys to dev AKS |
| D5 | Kong routes | DGD service routes accessible via Kong at `https://api.adports.ae/dgd/` |
| D6 | SonarQube config | Quality gate configured; PR comments enabled |
| D7 | Checkmarx SAST config | SAST scan runs; critical vulnerabilities fail pipeline |
| D8 | Snyk config | Dependency scan runs; CVSS > 9 fails pipeline |
| D9 | ArgoCD manifest | ArgoCD syncs from GitLab; auto-sync on merge to `main` |
| D10 | Gate 1 validation | Full DGD pilot passes all Gate 1 criteria (see below) |

---

## Generated GitLab CI Pipeline

```yaml
# Generated: .gitlab-ci.yml
stages:
  - build
  - test
  - security-scan
  - container-build
  - deploy-dev
  - integration-test
  - deploy-staging

variables:
  DOCKER_REGISTRY: ${ACR_LOGIN_SERVER}
  IMAGE_TAG: ${CI_COMMIT_SHA}
  HELM_RELEASE: ${SERVICE_NAME}-${CI_ENVIRONMENT_SLUG}

# ─── BUILD ────────────────────────────────────────────────────────────────────
dotnet-build:
  stage: build
  image: mcr.microsoft.com/dotnet/sdk:9.0
  script:
    - dotnet restore
    - dotnet build --no-restore -c Release
  cache:
    key: "$CI_PROJECT_ID-dotnet"
    paths: [.nuget/]

# ─── UNIT TESTS ───────────────────────────────────────────────────────────────
dotnet-test:
  stage: test
  image: mcr.microsoft.com/dotnet/sdk:9.0
  services:
    - name: postgres:16
      alias: postgres
  variables:
    POSTGRES_DB: test_db
    POSTGRES_PASSWORD: test_pass
  script:
    - dotnet test --no-build -c Release --collect:"XPlat Code Coverage" --results-directory coverage
  coverage: '/Line coverage: \d+\.\d+%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/**/coverage.cobertura.xml

# ─── SECURITY SCANS ───────────────────────────────────────────────────────────
sonarqube-scan:
  stage: security-scan
  image: sonarsource/sonar-scanner-cli:latest
  script:
    - sonar-scanner
      -Dsonar.host.url=${SONAR_HOST_URL}
      -Dsonar.login=${SONAR_TOKEN}
      -Dsonar.projectKey=${CI_PROJECT_PATH_SLUG}
      -Dsonar.qualitygate.wait=true
  allow_failure: false

checkmarx-sast:
  stage: security-scan
  image: checkmarx/cx-flow:latest
  script:
    - java -jar /app/cx-flow.jar
      --scan
      --app=${CI_PROJECT_NAME}
      --repo-url=${CI_PROJECT_URL}
      --branch=${CI_COMMIT_REF_NAME}
      --cx-token=${CHECKMARX_TOKEN}
      --bug-tracker=NONE
      --filter-severity=CRITICAL,HIGH
  allow_failure: false  # CRITICAL/HIGH vulnerabilities fail pipeline

snyk-scan:
  stage: security-scan
  image: snyk/snyk:dotnet
  script:
    - snyk test --severity-threshold=high --fail-on=upgradable
  allow_failure: false

trivy-scan:
  stage: security-scan
  image: aquasec/trivy:latest
  script:
    - trivy fs --exit-code 1 --severity CRITICAL,HIGH --ignore-unfixed .
  allow_failure: false

# ─── CONTAINER BUILD ──────────────────────────────────────────────────────────
docker-build:
  stage: container-build
  image: docker:24
  services: [docker:24-dind]
  before_script:
    - docker login -u ${ACR_USERNAME} -p ${ACR_PASSWORD} ${ACR_LOGIN_SERVER}
  script:
    - docker build -t ${DOCKER_REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG} .
    - docker push ${DOCKER_REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG}
    - docker tag ${DOCKER_REGISTRY}/${SERVICE_NAME}:${IMAGE_TAG} ${DOCKER_REGISTRY}/${SERVICE_NAME}:latest
    - docker push ${DOCKER_REGISTRY}/${SERVICE_NAME}:latest

# ─── DEPLOY DEV ───────────────────────────────────────────────────────────────
deploy-dev:
  stage: deploy-dev
  image: alpine/helm:3.15
  environment:
    name: dev
    url: https://dev.api.adports.ae/${SERVICE_SLUG}/
  script:
    - helm upgrade --install ${HELM_RELEASE}
        ./helm/${SERVICE_NAME}
        --namespace ${SERVICE_NAMESPACE}
        --values ./helm/${SERVICE_NAME}/values-dev.yaml
        --set image.tag=${IMAGE_TAG}
        --set image.repository=${DOCKER_REGISTRY}/${SERVICE_NAME}
        --atomic
        --timeout 5m
  only: [main]
```

---

## Pulumi IaC Generator

```typescript
// Generated: index.ts (per service Azure resources)
import * as azure from "@pulumi/azure-native";
import * as pulumi from "@pulumi/pulumi";

const config = new pulumi.Config();
const serviceName = config.require("serviceName");
const environment = pulumi.getStack();

// PostgreSQL database per service (tenant isolation via separate DB in shared cluster)
const dbRole = new azure.dbforpostgresql.Role(`${serviceName}-db-role`, {
    serverName: "adports-pg-cluster",
    resourceGroupName: "adports-data-rg",
    roleName: `${serviceName}_${environment}`,
    password: config.requireSecret("dbPassword"),
});

// Redis cache namespace (logical isolation via key prefix in shared Redis)
// No new Redis resource needed — uses shared cluster with service-specific key prefix

// Azure Blob Storage for service-specific files
const storageAccount = new azure.storage.StorageAccount(`${serviceName}sa`, {
    resourceGroupName: `adports-${environment}-rg`,
    sku: { name: azure.storage.SkuName.Standard_LRS },
    kind: azure.storage.Kind.StorageV2,
    enableHttpsTrafficOnly: true,
    allowBlobPublicAccess: false,
    minimumTlsVersion: azure.storage.MinimumTlsVersion.TLS1_2,
});

const container = new azure.storage.BlobContainer(`${serviceName}-artifacts`, {
    accountName: storageAccount.name,
    resourceGroupName: `adports-${environment}-rg`,
    publicAccess: azure.storage.PublicAccess.None,
});

export const storageAccountName = storageAccount.name;
export const storageContainerName = container.name;
```

---

## Kong Route Generator

```yaml
# Generated: kong-routes.yaml (applied via ArgoCD)
apiVersion: configuration.konghq.com/v1
kind: KongIngress
metadata:
  name: dgd-service-ingress
  namespace: dgd-prod
spec:
  route:
    methods: [GET, POST, PUT, DELETE, PATCH]
    strip_path: false
    preserve_host: true

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: dgd-service
  namespace: dgd-prod
  annotations:
    kubernetes.io/ingress.class: "kong"
    konghq.com/plugins: "jwt-auth,rate-limiting,request-id"
spec:
  rules:
    - host: api.adports.ae
      http:
        paths:
          - path: /dgd/
            pathType: Prefix
            backend:
              service:
                name: dgd-command-service
                port: { number: 80 }
```

---

## Gate 1 Criteria

Gate 1 validates that the platform can autonomously build a real project end-to-end:

| # | Criterion | Measurement |
|---|-----------|------------|
| G1.1 | Full DGD pilot (BRD→Architecture→Code→Deploy) completes in < 3 hours | Stopwatch on Ledger events |
| G1.2 | DGD declaration submission → SINTECE response flow works end-to-end | Integration test via Newman |
| G1.3 | All generated services pass `dotnet build` + `dotnet test` | CI pipeline green |
| G1.4 | SonarQube quality gate passes; 0 Checkmarx CRITICAL findings | Scan reports |
| G1.5 | Services deployed to dev AKS and responding on Kong routes | Health check via curl |
| G1.6 | Pipeline Ledger has signed entries for all 8 agent stages | Ledger explorer shows chain |
| G1.7 | Two-person approval enforced (Architect 1 + Architect 2 both signed) | Ledger approval entries |
| G1.8 | Azure cost for DGD pilot < $200 | Azure Cost Management dashboard |
| G1.9 | BRD stories not altered by AI without explicit approval | Audit log review |
| G1.10 | No credentials in generated code or git history | GitLeaks scan on all repos |

---

## Step-by-Step Execution Plan

### Week 1: Pipeline Generators

- [ ] Implement GitLab CI pipeline generator with all stages.
- [ ] Implement Azure DevOps pipeline generator (YAML format).
- [ ] Test: Generate pipeline for DGD service; all stages pass.

### Week 2: IaC + Helm + Kong

- [ ] Implement Pulumi TypeScript IaC generator.
- [ ] Implement Terraform HCL generator (alternative).
- [ ] Complete Helm chart generator (add missing files from Phase 12 scaffolds).
- [ ] Implement Kong route + plugin configuration generator.
- [ ] Test: `pulumi up` creates resources; Helm deploys to dev; Kong routes accessible.

### Week 3: Security Tools + ArgoCD

- [ ] Implement SonarQube project config generator (sonar-project.properties + quality gate assignment).
- [ ] Implement Checkmarx scan config generator.
- [ ] Implement Snyk policy file generator (.snyk).
- [ ] Implement Trivy config generator (trivy.yaml).
- [ ] Implement ArgoCD application manifest generator.
- [ ] Wire DevOps Agent to Orchestrator framework.

### Week 4: Gate 1 Validation

- [ ] Run full DGD pilot end-to-end (all agents: Architecture → Backend → Frontend → Database → Integration → DevOps).
- [ ] Validate all 10 Gate 1 criteria.
- [ ] Fix any issues found.
- [ ] Record Gate 1 pass/fail in Pipeline Ledger with all signed approvals.

---

*Phase 15 — DevOps & Infrastructure Agent (Gate 1 Checkpoint) — AI Portal — v1.0*
