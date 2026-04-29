---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend", "devops"]
---

# Security Requirements

## Authentication & Authorization

- All services authenticate via **Keycloak 25** JWT bearer tokens (realm: `ai-portal`)
- Services must validate: signature, expiry (`exp`), issuer (`iss`), audience (`aud`)
- Use **OpenFGA** for fine-grained RBAC checks on resources (project, artifact, skill, ledger-entry)
- Never implement custom authentication; always delegate to Keycloak
- Service-to-service calls use Keycloak client credentials flow with dedicated service accounts

## Secrets Management

- **All secrets in HashiCorp Vault** — never in code, config files, environment files, or K8s Secrets
- Use **Vault Agent Injector** (`vault.hashicorp.com/agent-inject-secret-*` annotations)
- Secret rotation: database credentials rotate every 30 days via Vault dynamic secrets
- No plaintext credentials in Git history — enforced by GitLeaks in CI pipeline
- Vault paths: `secret/data/orbit/<service-name>/<key>`

## Input Validation

- Validate all inputs at the API boundary using `FluentValidation` (.NET) or `pydantic` (Python)
- Sanitise HTML inputs using `HtmlSanitizer` before storage
- Reject requests with payloads > 10 MB
- Validate file uploads: MIME type whitelist, max size 50 MB, scan with ClamAV before processing

## SQL Injection Prevention

- Always use parameterised queries or ORM (`EF Core` / `SQLAlchemy`)
- Never concatenate user input into SQL strings
- Use `pg_trgm` or `to_tsquery` for full-text search — never `LIKE '%{input}%'`

## OWASP Top 10 Controls

| Risk | Control |
|---|---|
| A01 Broken Access Control | OpenFGA tuple checks on every resource operation |
| A02 Cryptographic Failures | TLS 1.3 everywhere; AES-256 at rest via Vault |
| A03 Injection | Parameterised queries; ORM; input validation |
| A04 Insecure Design | Threat modelling required for new Phase designs |
| A05 Security Misconfiguration | Helm chart security context; read-only root FS |
| A06 Vulnerable Components | Trivy + Checkmarx in CI; Fleet Upgrade Agent |
| A07 Auth Failures | Keycloak; MFA enforced for architects and admins |
| A08 Integrity Failures | SHA-256 chain in Pipeline Ledger; signed images |
| A09 Logging Failures | All auth events → Loki; audit log table |
| A10 SSRF | Allowlist outbound HTTP destinations per service |

## Container Security

- All containers must run as non-root (`runAsNonRoot: true`, `runAsUser: 10001`)
- Read-only root filesystem: `readOnlyRootFilesystem: true`
- Drop all capabilities: `capabilities: drop: [ALL]`
- No privileged containers unless explicitly approved by platform team
- Image pull policy: `Always`; images must come from `harbor.ai.adports.ae/orbit/`

## Network Policy

- Default deny all ingress and egress in `ai-portal` namespace
- Explicitly allow: service-to-service within namespace, egress to Vault, Keycloak, LiteLLM, PostgreSQL
- Kong API Gateway is the only external ingress; no direct NodePort services
