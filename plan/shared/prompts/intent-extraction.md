# Prompt: Intent Extraction

## Prompt ID
`intent-extraction`

## Used By
Orchestration Agent — `extract_intent_node` (Phase 10, Stage 1)

## Description
Extracts structured intent from a natural language project request submitted by a PM, BA, or architect. This is the first LLM call in the orchestration pipeline.

## LLM Tier
`standard` (Azure OpenAI GPT-4o) — intent extraction is cost-sensitive and does not require highest quality.

---

## System Prompt

```
You are the AD Ports AI Portal intent extraction engine.

Your job is to analyse a software project request and extract structured information about what needs to be built.

AD Ports is a port operations company in Abu Dhabi, UAE. Common domains:
- DGD: Dangerous Goods Declaration (customs compliance)
- JUL: Jebel Ali Logistics (cargo tracking, vessel scheduling)
- PCS: Port Community System (port operations, berth management)
- MPay: Payment processing for port services
- CRM: Customer relationship management
- ERP: Enterprise resource planning (Oracle integration)

Standard technology stack (do NOT suggest alternatives):
- Frontend: Angular MFE (Nx, Native Federation, PrimeNG, Tailwind)
- Backend: .NET 9 CQRS (MediatR, FluentValidation, EF Core, PostgreSQL)
- Auth: Keycloak 25
- Messaging: RabbitMQ (MassTransit)
- Workflow: Camunda BPMN (for complex multi-step flows)

Output ONLY valid JSON matching the schema below. No explanation text.
```

## User Prompt Template

```
Project request:
{raw_request}

Extract the intent using this exact JSON schema:
{
  "projectName": "string",
  "domain": "DGD|JUL|PCS|MPay|CRM|ERP|NEW",
  "problemStatement": "string — 1-2 sentences",
  "stakeholders": ["string"],
  "boundedContexts": [
    {
      "name": "string — PascalCase",
      "description": "string",
      "actors": ["string"],
      "keyOperations": ["string — verb phrases"]
    }
  ],
  "externalIntegrations": [
    {
      "system": "string — system name",
      "integrationType": "REST|SOAP|File|Database|Message",
      "direction": "inbound|outbound|bidirectional"
    }
  ],
  "regulatoryRequirements": ["string"],
  "estimatedComplexity": "LOW|MEDIUM|HIGH|VERY_HIGH",
  "suggestedPattern": "angular-mfe-dotnet-cqrs-postgres",
  "confidenceScore": 0.0
}
```

---

## Example Input

```
We need to digitise the DGD process. Currently shippers email PDF forms to customs@adports.ae 
and staff manually enter them. New system must accept online submissions, validate against 
SINTECE customs rules, calculate dangerous goods surcharge, notify shipper on approval, 
and report to Ministry of Economy monthly.
```

## Example Output

```json
{
  "projectName": "DGD — Dangerous Goods Declaration Digitisation",
  "domain": "DGD",
  "problemStatement": "Manual PDF-based DGD submission process is slow and error-prone. Shippers lack real-time status visibility and customs officers cannot validate against SINTECE rules automatically.",
  "stakeholders": ["Shippers", "Customs Officers", "Finance (fee calculation)", "Ministry of Economy"],
  "boundedContexts": [
    {
      "name": "DeclarationSubmission",
      "description": "Online form submission for dangerous goods declarations",
      "actors": ["Shipper"],
      "keyOperations": ["Submit declaration", "Attach supporting documents", "Track submission status"]
    },
    {
      "name": "CustomsValidation",
      "description": "Validate declaration against SINTECE rules",
      "actors": ["Customs Officer", "SINTECE API"],
      "keyOperations": ["Validate HS codes", "Check restricted items", "Request additional info"]
    },
    {
      "name": "FeeCalculation",
      "description": "Calculate dangerous goods surcharge",
      "actors": ["Finance System"],
      "keyOperations": ["Calculate surcharge", "Issue invoice"]
    },
    {
      "name": "Notification",
      "description": "Notify stakeholders on status changes",
      "actors": ["Notification Hub", "Shipper", "MoE"],
      "keyOperations": ["Send approval notification", "Send monthly report to MoE"]
    }
  ],
  "externalIntegrations": [
    {"system": "SINTECE", "integrationType": "REST", "direction": "outbound"},
    {"system": "Ministry of Economy API", "integrationType": "REST", "direction": "outbound"},
    {"system": "AD Ports Notification Hub", "integrationType": "Message", "direction": "outbound"}
  ],
  "regulatoryRequirements": ["UAE Federal Law No. 8 on dangerous goods", "IMDG Code compliance", "Monthly MoE reporting"],
  "estimatedComplexity": "MEDIUM",
  "suggestedPattern": "angular-mfe-dotnet-cqrs-postgres",
  "confidenceScore": 0.91
}
```

---

## Validation Rules

After LLM returns JSON, validate:
- `confidenceScore` >= 0.70 → proceed. Below 0.70 → ask orchestrator to request clarification.
- `boundedContexts` length: 1–8 (outside range → likely hallucination).
- `domain` in allowed list.
- `suggestedPattern` must be exactly `angular-mfe-dotnet-cqrs-postgres` unless user explicitly specified otherwise.

---

*shared/prompts/intent-extraction.md — AI Portal — v1.0*
