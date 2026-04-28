# Prompt: BRD / HLD Document Parser

## Prompt ID
`brd-parser`

## Used By
Orchestration Agent — `parse_brd_node` (Phase 10, Stage 2)

## Description
Parses a Business Requirements Document (BRD), High-Level Design (HLD), or Integration Control Document (ICD) into a structured data model that the Orchestrator uses for component decomposition. The extracted structure drives story generation, architecture proposal, and QA plan generation.

## LLM Tier
`standard` (Azure OpenAI GPT-4o) — document analysis is cost-sensitive; GPT-4o handles long documents well.

---

## System Prompt

```
You are the AD Ports AI Portal document analyst.

Your job is to parse a business requirements or design document and extract its structured content.

AD Ports is a port operations company in Abu Dhabi, UAE. Be aware of domain terminology:
- DGD: Dangerous Goods Declaration
- JUL: Jebel Ali Logistics
- PCS: Port Community System  
- MPay: Payment Gateway for port services
- SINTECE: UAE Customs clearance integration platform
- Ministry of Economy: UAE government counterparty for customs
- ISPS: International Ship and Port Facility Security
- EDI: Electronic Data Interchange (common in port/logistics systems)

When parsing acceptance criteria, look for patterns like:
- "The system shall..." / "The system must..."
- "Given/When/Then" (BDD-style)
- "AC-XXX-NNN:" (AD Ports acceptance criteria ID format)
- Bullet lists under a "Acceptance Criteria" or "Functional Requirements" heading

Output ONLY valid JSON matching the schema below. No explanation text outside JSON.
```

---

## User Prompt Template

```
Document content (may be truncated):
<document>
{document_text}
</document>

Extract the document content using this exact JSON schema:
{
  "documentType": "BRD|HLD|ICD|FRD|SRS|OTHER",
  "documentTitle": "string",
  "documentVersion": "string|null",
  "projectName": "string",
  "domain": "DGD|JUL|PCS|MPay|CRM|ERP|NEW|UNKNOWN",

  "sections": [
    {
      "id": "string",
      "title": "string",
      "summary": "string — 1-3 sentences",
      "sectionType": "background|scope|requirements|architecture|integration|security|non-functional|other"
    }
  ],

  "userRoles": [
    {
      "name": "string",
      "description": "string",
      "permissions": ["string"]
    }
  ],

  "acceptanceCriteria": [
    {
      "id": "string — use AC-XXX-NNN format",
      "title": "string — short name",
      "given": "string|null",
      "when": "string|null",
      "then": "string",
      "priority": "MUST|SHOULD|COULD|WONT",
      "category": "functional|security|performance|accessibility|integration"
    }
  ],

  "externalIntegrations": [
    {
      "system": "string",
      "purpose": "string",
      "protocol": "REST|SOAP|File|Database|Message|EDI|OTHER",
      "direction": "inbound|outbound|bidirectional",
      "dataClassification": "PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED"
    }
  ],

  "nonFunctionalRequirements": [
    {
      "category": "performance|security|availability|scalability|accessibility|compliance",
      "requirement": "string",
      "measurable": true
    }
  ],

  "regulatoryReferences": ["string"],
  "assumptionsAndConstraints": ["string"],
  "openIssues": ["string"],
  "ambiguities": ["string — areas where document is unclear or contradictory"]
}
```

---

## Example Input

```
PROJECT: DGD Digitization
VERSION: 1.2

BACKGROUND
Dangerous Goods Declarations are currently submitted via email as PDF forms to customs@adports.ae.
Manual entry takes 2-3 days. The new system will allow online submission with real-time SINTECE validation.

ROLES
- Customs Officer: Review and approve declarations. Can override SINTECE rejections with documented reason.
- Shipper: Submit declarations, view status, receive notifications.
- Supervisor: Override approvals, view analytics dashboard.

ACCEPTANCE CRITERIA
AC-DGD-001: Given a shipper submits a valid DGD form, the system shall validate against SINTECE within 30 seconds.
AC-DGD-002: The system must calculate dangerous goods surcharge automatically for Classes 1-9.
AC-DGD-003: Shippers must receive email and SMS notification within 5 minutes of status change.

INTEGRATIONS
- SINTECE API (REST, outbound): Real-time customs validation
- Ministry of Economy API (SOAP, outbound): Reporting declarations
- AD Ports Notification Hub (Message, outbound): Email/SMS delivery

SECURITY
- MFA required for all Customs Officer logins.
- All declaration data classified as CONFIDENTIAL.
```

---

## Example Output

```json
{
  "documentType": "BRD",
  "documentTitle": "DGD Digitization Requirements",
  "documentVersion": "1.2",
  "projectName": "DGD — Dangerous Goods Declaration Digitization",
  "domain": "DGD",

  "userRoles": [
    {
      "name": "customs_officer",
      "description": "Review and approve declarations",
      "permissions": ["review", "approve", "reject", "override_sintece"]
    },
    {
      "name": "shipper",
      "description": "Submit declarations, track status",
      "permissions": ["submit", "view_own", "receive_notifications"]
    },
    {
      "name": "supervisor",
      "description": "Override approvals, view analytics",
      "permissions": ["override", "view_all", "analytics"]
    }
  ],

  "acceptanceCriteria": [
    {
      "id": "AC-DGD-001",
      "title": "SINTECE validation within 30 seconds",
      "given": "a shipper submits a valid DGD form",
      "when": null,
      "then": "the system shall validate against SINTECE within 30 seconds",
      "priority": "MUST",
      "category": "integration"
    },
    {
      "id": "AC-DGD-002",
      "title": "Automatic surcharge calculation",
      "given": null,
      "when": null,
      "then": "The system must calculate dangerous goods surcharge automatically for Classes 1-9",
      "priority": "MUST",
      "category": "functional"
    }
  ],

  "externalIntegrations": [
    {
      "system": "SINTECE",
      "purpose": "Real-time customs validation",
      "protocol": "REST",
      "direction": "outbound",
      "dataClassification": "CONFIDENTIAL"
    }
  ],

  "ambiguities": [
    "Override reason for SINTECE rejection — is this free text or from a controlled list?",
    "Dangerous goods surcharge formula not specified — what is the calculation basis?"
  ]
}
```

---

## Validation Rules

- `acceptanceCriteria` array must have `length >= 1`; if none found in document, create synthetic AC from background section
- `ambiguities` must be surfaced to the human reviewer before Architecture Proposal starts
- `domain` must match one of the AD Ports known domains; use `NEW` when genuinely novel
- IDs must use `AC-{DOMAIN}-{NNN}` format where `{DOMAIN}` is 2–5 uppercase letters
- `nonFunctionalRequirements` must include at least one `performance` entry if document mentions response times

---

*BRD Parser Prompt — AD Ports AI Portal — v1.0 — Owner: Orchestrator Squad*
