# Instructions — Phase 15: DevOps & Infrastructure Agent

> Add this file to your IDE's custom instructions when building or extending the DevOps Agent.

---

## Context

You are building the **AD Ports DevOps & Infrastructure Agent** — an agent that generates complete CI/CD pipelines (GitLab CI and Azure DevOps), Helm charts, Pulumi IaC, Kong Ingress routes, and ArgoCD manifests for any AD Ports service. All generated artefacts must pass the AD Ports security gates (SonarQube, Checkmarx, Snyk, Trivy) on first attempt.

---

## Pipeline Template Structure

```yaml
# MANDATORY pipeline stages order (GitLab CI template)
# .gitlab-ci.yml skeleton generated for every service

stages:
  - build        # dotnet build / npm ci + ng build
  - test         # Unit tests + integration tests (Testcontainers)
  - sast         # Checkmarx SAST + Semgrep
  - sca          # Snyk dependency scan + license check
  - quality      # SonarQube quality gate
  - container    # Docker build + Trivy image scan
  - deploy-dev   # ArgoCD sync to dev namespace
  - integration  # Newman integration tests against dev
  - deploy-staging # ArgoCD sync to staging
  - e2e          # Playwright E2E against staging
  - security     # OWASP ZAP (staging only)
  # deploy-prod is MANUAL — requires Pipeline Ledger approval entry
  - deploy-prod
```

## GitLab CI Generation Pattern

```python
# agents/devops_agent/templates/gitlab-ci.scriban.yaml
stages: [build, test, sast, sca, quality, container, deploy-dev, integration, deploy-staging, e2e, deploy-prod]

variables:
  DOTNET_IMAGE: mcr.microsoft.com/dotnet/sdk:9.0
  DOCKER_REGISTRY: {{ acr_name }}.azurecr.io
  SERVICE_NAME: {{ service_name | downcase }}
  NAMESPACE: {{ aks_namespace }}

# ── Build ──────────────────────────────────────────────────────────────────
build:
  stage: build
  image: $DOTNET_IMAGE
  script:
    - dotnet restore src/{{ solution_name }}.sln
    - dotnet build src/{{ solution_name }}.sln --configuration Release --no-restore
  artifacts:
    paths: [publish/]

# ── Unit Tests ────────────────────────────────────────────────────────────
unit-tests:
  stage: test
  image: $DOTNET_IMAGE
  script:
    - dotnet test tests/{{ solution_name }}.UnitTests --collect:"XPlat Code Coverage" --results-directory coverage/
  coverage: '/Total\s+\|\s+(\d+\.?\d*)%/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage/**/coverage.cobertura.xml

# ── SAST: Checkmarx ────────────────────────────────────────────────────────
checkmarx-sast:
  stage: sast
  image: checkmarx/ast-cli:latest
  script:
    - cx scan create --project-name $SERVICE_NAME --branch $CI_COMMIT_BRANCH --source .
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'

# ── Container scan: Trivy ──────────────────────────────────────────────────
trivy-scan:
  stage: container
  image: aquasec/trivy:latest
  script:
    - trivy image --severity HIGH,CRITICAL --exit-code 1 $DOCKER_REGISTRY/$SERVICE_NAME:$CI_COMMIT_SHA
  needs: [docker-build]

# ── Deploy to dev (ArgoCD) ─────────────────────────────────────────────────
deploy-dev:
  stage: deploy-dev
  image: argoproj/argocd:v2.12.0
  script:
    - argocd app sync ai-portal-$SERVICE_NAME-dev --timeout 300
    - argocd app wait ai-portal-$SERVICE_NAME-dev --health --timeout 300
  environment:
    name: dev
    url: https://$SERVICE_NAME-dev.adports.ae

# ── Deploy to prod (manual gate) ────────────────────────────────────────────
deploy-prod:
  stage: deploy-prod
  image: argoproj/argocd:v2.12.0
  when: manual
  script:
    - argocd app sync ai-portal-$SERVICE_NAME-prod --timeout 300
  environment:
    name: production
    url: https://$SERVICE_NAME.adports.ae
  rules:
    - if: '$CI_COMMIT_BRANCH == "main"'
```

## Helm Chart Generation Rules

```yaml
# REQUIRED: All Helm charts must have these features
# - values.yaml validates against adports-helm-chart.values.schema.json
# - templates/deployment.yaml uses non-root security context
# - templates/hpa.yaml with min 2 / max 10 replicas
# - templates/pdb.yaml with minAvailable: 1
# - templates/networkpolicy.yaml with deny-all ingress + specific allow rules

# security context (MANDATORY in deployment.yaml)
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]
```

## Pulumi IaC Generation Rules

```typescript
// Generated Pulumi TypeScript — required patterns

// CORRECT: Use Pulumi Config for environment values
const config = new pulumi.Config();
const environment = config.require("environment");  // dev | staging | prod

// CORRECT: Resource naming convention
const namespace = new k8s.core.v1.Namespace(`ai-portal-${serviceName}`, {
  metadata: {
    name: `ai-portal-${serviceName}`,
    labels: {
      "app.kubernetes.io/part-of": "ai-portal",
      "adports.ae/domain": domain,
      "adports.ae/environment": environment,
    }
  }
});

// WRONG: Hardcoded environment
const ns = new k8s.core.v1.Namespace("ai-portal-dgd-prod", { /* hardcoded */ });
```

## Kong Ingress Route Generation

```yaml
# Generated KongIngress for every service
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: {{ service_name }}-jwt
  namespace: {{ aks_namespace }}
config:
  uri_param_names: [jwt]
  cookie_names: []
  key_claim_name: iss
  claims_to_verify: [exp]
plugin: jwt
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {{ service_name }}
  namespace: {{ aks_namespace }}
  annotations:
    konghq.com/plugins: "{{ service_name }}-jwt,rate-limiting"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: kong
  tls:
    - hosts: [{{ service_name }}.adports.ae]
      secretName: {{ service_name }}-tls
  rules:
    - host: {{ service_name }}.adports.ae
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {{ service_name }}
                port:
                  number: 80
```

## ArgoCD Manifest Validation

All generated ArgoCD `Application` manifests must validate against `adports-argocd-app.schema.json`:

```python
import jsonschema, json

def validate_argocd_manifest(manifest: dict) -> None:
    schema = json.loads(Path("shared/specs/adports-argocd-app.schema.json").read_text())
    jsonschema.validate(manifest, schema)
    # Also validate namespace naming
    namespace = manifest["spec"]["destination"]["namespace"]
    assert namespace.startswith("ai-portal-"), f"Namespace {namespace} must start with 'ai-portal-'"
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `deploy-prod` stage without `when: manual` | Production deploys must always be explicit human actions |
| Missing `trivy-scan` stage | Container scanning is non-negotiable |
| `--skip-checks` on Checkmarx/SonarQube | Quality gates cannot be bypassed in generated pipelines |
| `allowPrivilegeEscalation: true` in Helm templates | Security policy violation |
| `kubectl apply` commands in pipelines | All K8s deployments via ArgoCD (GitOps only) |
| Secrets in `values.yaml` or `gitlab-ci.yml` | Use Vault — all secrets must be injected at runtime |

---

*Instructions — Phase 15 — AD Ports AI Portal — Applies to: Delivery Agents Squad*
