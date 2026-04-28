# AD Ports Security Baseline

## Applies To

All agents, generated services, and infrastructure managed by the AI Portal. This is a non-negotiable baseline — all generated code and configuration must comply before any artifact is approved.

---

## Authentication & Authorization

### Keycloak Requirements

- Every service must validate JWT Bearer tokens from Keycloak `portal` realm.
- Use `Authority` and `Audience` from configuration — never hardcode.
- Extract user ID from `sub` claim; roles from `realm_access.roles`.
- Service-to-service calls use Keycloak client credentials grant (not user tokens).

### OpenFGA Authorization

- Fine-grained authorization for all data access uses OpenFGA.
- Never implement custom RBAC — use OpenFGA `check` call before any data access.
- Authorization model changes require Governance Squad review.

---

## Secrets Management

```
RULE: Zero secrets in code, configuration files, environment variables, or git history.

All secrets MUST come from:
  - Vault Agent Injector (mounted as files in /vault/secrets/)
  - Kubernetes Secrets (populated by Vault — never created manually)
  - Azure Key Vault (for Azure resource credentials)

Forbidden:
  - Secrets in appsettings.json (except empty placeholder strings)
  - Secrets in Helm values.yaml committed to git
  - Secrets in .env files committed to git
  - Base64-encoded secrets in Kubernetes manifests committed to git
```

---

## Network Security

- TLS 1.2+ on all service-to-service communication.
- mTLS between services in the same AKS cluster (Istio/cert-manager).
- All external APIs consumed via Kong API Gateway (not direct HTTP from pods).
- Network Policies: pods may only communicate with explicitly allowed namespaces.
- No `hostNetwork: true` in pod specs.
- No `hostPort` mappings.

---

## Container Security

```dockerfile
# REQUIRED: Non-root user in all Dockerfiles
USER app:app

# REQUIRED: No SETUID binaries
RUN find / -perm /4000 -type f -delete 2>/dev/null || true

# REQUIRED: Read-only root filesystem (where possible)
# In Helm deployment.yaml:
# securityContext:
#   readOnlyRootFilesystem: true
#   runAsNonRoot: true
#   allowPrivilegeEscalation: false
#   capabilities:
#     drop: [ALL]

# REQUIRED: Minimal base images
FROM mcr.microsoft.com/dotnet/aspnet:9.0-alpine  # NOT mcr.microsoft.com/dotnet/aspnet:9.0
```

---

## SQL Injection Prevention

```csharp
// CORRECT: LINQ queries (EF Core handles parameterization)
var declaration = await _context.Declarations
    .Where(d => d.ReferenceNumber == referenceNumber)
    .FirstOrDefaultAsync(cancellationToken);

// CORRECT: Parameterized raw SQL when needed
await _context.Database.ExecuteSqlInterpolated(
    $"SELECT * FROM dgd.declarations WHERE id = {id}");

// WRONG: String concatenation in SQL
// $"SELECT * FROM declarations WHERE id = '{id}'"  ← SQL INJECTION RISK
```

---

## Input Validation

```csharp
// ALL external inputs must be validated with FluentValidation before processing
// Validation happens in MediatR ValidationBehaviour BEFORE handler executes

// Example validator rules for security-relevant fields
RuleFor(x => x.RedirectUri)
    .Must(uri => uri.StartsWith("https://") && IsAllowedDomain(uri))
    .WithMessage("Redirect URI must be an approved HTTPS domain.");

RuleFor(x => x.HtmlContent)
    .Must(html => !ContainsDangerousTags(html))  // No <script>, <iframe> etc.
    .WithMessage("HTML content contains disallowed elements.");

// File uploads: validate type, size, and scan for malware
RuleFor(x => x.UploadedFile)
    .Must(f => AllowedFileExtensions.Contains(Path.GetExtension(f.FileName).ToLower()))
    .Must(f => f.Length <= 50 * 1024 * 1024)  // Max 50MB
    .WithMessage("Invalid file type or size.");
```

---

## Output Encoding

```typescript
// Angular: NEVER use innerHTML with user content (XSS)
// WRONG:
// this.element.nativeElement.innerHTML = userContent;

// CORRECT: Angular's built-in sanitization
// Use [innerHTML] only with DomSanitizer.bypassSecurityTrustHtml() for trusted content
// Prefer text interpolation {{ value }} which auto-escapes

// WRONG: Bypassing sanitization without good reason
// this.sanitizer.bypassSecurityTrustHtml(userInput)  ← REQUIRES security review
```

---

## Logging Security

```
DO LOG:
  - User ID (never full name or email in structured logs)
  - Action performed (e.g., "declaration.submitted")
  - Resource ID (e.g., declaration ID)
  - Result (success/failure)
  - Timestamp
  - Correlation ID

DO NOT LOG:
  - Passwords
  - JWT tokens (full value)
  - Credit/debit card numbers
  - National IDs, passport numbers
  - Bank account numbers
  - Health records
  - Any data classified as CONFIDENTIAL or CLASSIFIED
```

---

## Dependency Management

```
RULE: All dependencies must pass:
  1. Snyk SCA scan — no HIGH/CRITICAL CVEs
  2. License compatibility check — no GPL-3.0 in commercial software
  3. Supply chain check — packages from official registries only (npmjs.org, nuget.org, pypi.org)

Update cadence:
  - Security patches: within 72 hours of disclosure
  - Minor updates: within 2 sprints
  - Major updates: within 90 days (governed by Framework Lifecycle Policy)
```

---

## OWASP Top 10 Checklist

Every generated service is verified against:

| # | OWASP Risk | Mitigation |
|---|------------|-----------|
| A01 | Broken Access Control | OpenFGA checks on every resource; no client-side auth |
| A02 | Cryptographic Failures | TLS 1.2+, AES-256 at rest, Vault for key mgmt |
| A03 | Injection | Parameterized queries, FluentValidation, input sanitization |
| A04 | Insecure Design | Threat model reviewed per domain; defense in depth |
| A05 | Security Misconfiguration | Trivy scans; no default creds; no debug modes in prod |
| A06 | Vulnerable Components | Snyk SCA in every CI pipeline; auto-alert on new CVEs |
| A07 | Authentication Failures | Keycloak 25, MFA enforced, JWT validation strict |
| A08 | Software Integrity Failures | Signed container images; SBOM generated per release |
| A09 | Security Logging Failures | OpenTelemetry traces; Pipeline Ledger; Loki log aggregation |
| A10 | SSRF | External HTTP calls only via approved Kong routes; no free-form URLs |

---

## PCI-DSS Addendum (MPay Domain Only)

- No storage of full Primary Account Number (PAN) — store only last 4 digits.
- No CVV/CVC storage under any circumstances.
- All cardholder data encrypted with AES-256; keys in Azure Key Vault.
- PCI-DSS scoped services isolated in separate AKS namespace with restricted Network Policy.
- Quarterly penetration test required for PCI scope.

---

*shared/instructions/security-baseline.md — AI Portal — v1.0*
