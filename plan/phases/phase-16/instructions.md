# Instructions — Phase 16: Security Hardening

> Add this file to your IDE's custom instructions when performing security hardening or vulnerability remediation.

---

## Context

You are working on **security hardening** for the AD Ports AI Portal — applying OWASP Top 10 mitigations, Kubernetes Pod Security Standards, network policies, secrets rotation, and security scanning integration. This phase runs in parallel with feature development and enforces non-negotiable security baselines.

---

## OWASP Top 10 Checklist for Generated Services

Every generated service must pass:

| OWASP ID | Control | Verification |
|----------|---------|--------------|
| A01 Broken Access Control | OpenFGA check on every endpoint | `GET /api/{resource}` returns 403 without valid OpenFGA check |
| A02 Cryptographic Failures | No plaintext credentials in any config file | Checkmarx + Semgrep SAST scan passes |
| A03 Injection | Parameterised queries only (EF Core) | No raw SQL in codebase |
| A04 Insecure Design | Input validation on all API boundaries | FluentValidation on all commands |
| A05 Security Misconfiguration | No debug endpoints in production | `ASPNETCORE_ENVIRONMENT=Production` disables swagger |
| A06 Vulnerable Components | Snyk SCA passes | No HIGH/CRITICAL CVEs in direct dependencies |
| A07 Auth Failures | JWT verification on all endpoints | No endpoint returns 200 without valid Keycloak JWT |
| A09 Logging Failures | No sensitive data in logs | `SensitiveDataRedaction` middleware on all services |
| A10 SSRF | No user-controlled URLs in backend | All external URLs are whitelisted in `appsettings.json` |

## Kubernetes Pod Security Standards

```yaml
# REQUIRED security context for all AKS pods
securityContext:
  runAsNonRoot:             true
  runAsUser:                1000
  readOnlyRootFilesystem:   true
  allowPrivilegeEscalation: false
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop: ["ALL"]

# REQUIRED: Network policy — deny all ingress by default, allow only needed
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: {service-name}-network-policy
spec:
  podSelector:
    matchLabels:
      app: {service-name}
  policyTypes: [Ingress, Egress]
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: ai-portal-gateway    # Only Kong gateway can reach the service
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: ai-portal-data       # Only to data tier
```

## Secrets Management Pattern

```
Vault Agent Injector pattern (mandatory for all secrets):

1. Secret stored in: vault/secret/ai-portal/{service}/{env}/{secret-name}
2. Vault Agent Injector annotation in Pod spec:
   vault.hashicorp.com/agent-inject: "true"
   vault.hashicorp.com/agent-inject-secret-db: "secret/ai-portal/dgd/prod/db-password"
   vault.hashicorp.com/agent-inject-template-db: |
     {{- with secret "secret/ai-portal/dgd/prod/db-password" -}}
     ConnectionStrings__Default={{ .Data.data.value }}
     {{- end }}
3. Secret mounted as environment file at /vault/secrets/
4. Service reads via IConfiguration (not direct file read)

FORBIDDEN: ConfigMaps with secrets, environment variables with credentials in YAML
```

## Security Scanning Gates

CI/CD must have these gates — all BLOCK the pipeline on failure:

```yaml
# SonarQube quality gate (blocks on)
- Security Hotspots: 0 unresolved
- Vulnerabilities: 0 HIGH or CRITICAL
- Code Smells: <5% (does not block)

# Checkmarx SAST (blocks on)
- CRITICAL: any finding
- HIGH: any finding
- MEDIUM: blocks only on merge to main

# Snyk SCA (blocks on)
- CRITICAL CVE in direct dependency
- HIGH CVE in direct dependency with available fix

# Trivy container scan (blocks on)
- CRITICAL CVE in base image
- HIGH CVE in base image layers added by us
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `app.UseDeveloperExceptionPage()` without env check | Exposes stack traces in production |
| Logging `request.Body` or full request objects | Logs may capture credentials/PII |
| `Skip()` or `Disable()` on security middleware | Never bypass for convenience |
| `allowPrivilegeEscalation: true` | Root containers are a critical finding |
| Disabling HTTPS redirect | All Portal traffic is TLS |

---

*Instructions — Phase 16 — AD Ports AI Portal — Applies to: All Squads (Security is Everyone's Responsibility)*
