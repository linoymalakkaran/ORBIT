# NESA UAE Cybersecurity Framework Compliance Checklist
# Phase 25 — Gate 4: Sovereign AI + Compliance

## NESA UAE Cybersecurity Framework (aligned with ISO 27001)

### Domain 1: Information Asset Management
- [x] All services registered in Project Registry with data classification
- [x] Vault secret inventory maintained (see `infra/vault/policies.yaml`)
- [x] Harbor image registry with signed images (Harbor Notary)
- [ ] Data classification labels on all Kubernetes secrets (TODO: label all secrets)

### Domain 2: Identity & Access Management
- [x] Keycloak SSO for all users (realm: ai-portal)
- [x] Keycloak MFA enforced for admin roles
- [x] OpenFGA fine-grained RBAC (project-level permissions)
- [x] OPA Guardrails policy enforcement (Phase 18)
- [x] Vault dynamic secrets (no static credentials)
- [x] Service accounts per pod (no shared SA)
- [x] Kong JWT auth on all API ingress routes

### Domain 3: Physical & Environmental Security
- [x] On-premise deployment on vSphere 8 (no public cloud for classified data)
- [x] Sovereign AI on isolated GPU nodes (sovereign-ai namespace)
- [x] NetworkPolicies default-deny (Phase 18 reverification)

### Domain 4: Operations Security
- [x] All agent actions evaluated by OPA before execution (Phase 18)
- [x] Immutable audit trail in EventStoreDB (Pipeline Ledger, Phase 5)
- [x] Full observability: Prometheus + Grafana + Loki + Tempo (Phase 22)
- [x] Automated security scanning: Trivy (containers), SonarQube (SAST), GitLeaks (secrets)
- [x] Pod Security Standards: restricted policy on sovereign-ai namespace

### Domain 5: Communications Security
- [x] TLS everywhere (cert-manager + adports-internal-ca)
- [x] mTLS between services (via Antrea network policy + Kong)
- [x] Secrets never in environment variables (Vault Agent Injector)

### Domain 6: System Acquisition, Development & Maintenance
- [x] Generated code goes through SonarQube + Checkmarx before deployment
- [x] PR Review Agent enforces coding standards
- [x] All pipelines include Trivy container scan with CRITICAL exit
- [x] SBOM generation (Trivy SBOM mode) in CI pipeline

### Domain 7: Supplier Relationships
- [x] All LLM calls routed through LiteLLM gateway (no direct external API calls)
- [x] Classified data uses sovereign Llama model (no data leaves on-premise)
- [ ] Third-party dependency audit report (TODO: Snyk Organization report)

### SOC-2 Type II Readiness

#### CC1 — Control Environment
- [x] Role-based access control (Keycloak + OpenFGA)
- [x] Policy enforcement (OPA Guardrails)
- [x] Audit log retention (EventStoreDB + Loki, 1 year)

#### CC2 — Communication & Information
- [x] All policy decisions logged to Pipeline Ledger
- [x] Alert routing to Portal notifications + Grafana alerts

#### CC3 — Risk Assessment
- [x] Vulnerability Radar continuous scanning (Phase 23)
- [x] Health Monitor anomaly detection (Phase 20)

#### CC6 — Logical & Physical Access Controls
- [x] Zero-trust networking (NetworkPolicies default-deny)
- [x] Vault dynamic credentials (secrets expire automatically)
- [x] Harbor image scanning + signing

#### CC7 — System Operations
- [x] ArgoCD GitOps (all changes via git, no manual kubectl apply in prod)
- [x] PodDisruptionBudgets on all stateful services
- [x] HPA on all scalable services

#### CC8 — Change Management
- [x] All changes via PR + PR Review Agent
- [x] ArgoCD approval gate for production deploys
- [x] Pipeline Ledger immutable record of all deployments
