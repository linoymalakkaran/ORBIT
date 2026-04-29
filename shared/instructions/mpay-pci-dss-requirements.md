---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend", "devops"]
---

# MPay PCI-DSS Requirements

## Scope

This document applies to all services that handle, transmit, or store payment card data for the **MPay** payment platform. Non-compliance blocks deployment.

## PCI-DSS Applicable Controls (v4.0)

### Requirement 1 — Network Security

- Cardholder Data Environment (CDE) must be in a dedicated Kubernetes namespace: `mpay-cde`
- CDE namespace has strict NetworkPolicy: deny-all ingress/egress, allow only MPay API → payment gateway
- No direct internet access from CDE pods; all egress via approved proxy
- Quarterly network penetration tests required

### Requirement 2 — Secure Configurations

- No vendor-supplied defaults (passwords, keys) in any MPay service
- All MPay services use unique Vault-generated credentials
- MPay service containers: `runAsNonRoot: true`, `readOnlyRootFilesystem: true`, `allowPrivilegeEscalation: false`
- Disable all unused ports, protocols, services on MPay pods

### Requirement 3 — Cardholder Data Protection

- **PAN storage prohibited** — never log, store, or cache Primary Account Numbers
- Masking in logs: last 4 digits only (`**** **** **** 1234`)
- CVV2/CVC2: never store after authorisation, even encrypted
- Use tokenisation via MPay gateway — store only the payment token (non-sensitive)
- Encryption at rest: AES-256 for any incidental card data; keys in Vault

### Requirement 4 — Transmission Security

- TLS 1.3 exclusively for all card data in transit; TLS 1.2 only with approved cipher suites
- No card data in URLs, query strings, or logs
- Certificate pinning for MPay gateway connections

### Requirement 6 — Secure Development

- SAST (Checkmarx) + DAST scan required for every MPay service release
- No critical or high SAST findings allowed in production deployments
- Vulnerability patching SLA: Critical = 24h, High = 7 days, Medium = 30 days
- Penetration test annually and after significant changes

### Requirement 7 — Access Control

- Principle of least privilege: MPay service accounts in Vault have read-only access to their own secrets only
- No shared accounts — each MPay service has a dedicated Keycloak service account
- Multi-factor authentication required for all MPay production access

### Requirement 10 — Logging & Monitoring

- All access to cardholder data logged with: user ID, date/time, action, affected resource
- Logs retained for 12 months (3 months immediately available)
- Real-time alerts for: failed auth attempts > 5, cardholder data access outside business hours
- Logs in Loki with 12-month retention policy

### Requirement 12 — Security Policy

- Incident response plan must include cardholder data breach procedure
- Annual PCI-DSS self-assessment questionnaire (SAQ-D for service providers)
- Third-party vendor PCI compliance verification annually

## Code Review Checklist for MPay Services

Before merging any PR for MPay services:

- [ ] No PAN data in logs, comments, or test fixtures
- [ ] Payment token used instead of raw card number
- [ ] Vault secret references used (no hardcoded credentials)
- [ ] Network egress only to approved payment gateway endpoints
- [ ] RLS policy prevents cross-tenant data access
- [ ] Checkmarx SAST: zero HIGH/CRITICAL findings
- [ ] `pci-certified` role required for production deployment approval (OpenFGA check)
