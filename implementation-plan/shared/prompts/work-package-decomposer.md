# Prompt: Work Package Decomposer

## Prompt ID
`work-package-decomposer`

## Used By
Orchestration Agent — `decompose_work_node` (Phase 10, Stage 4)

## Description
Takes the structured intent and BRD output and decomposes the project into discrete `WorkPackage` objects — each corresponding to a specific specialist agent delegation. This is the planning step that determines WHAT the agents will build, in what order, with what inputs and expected outputs.

## LLM Tier
`premium` (Claude Sonnet 4.x) — decomposition quality directly determines scaffold quality. Underspending here leads to misaligned agent outputs.

---

## System Prompt

```
You are the AD Ports AI Portal work package decomposition engine.

You receive a structured project intent and BRD analysis and must produce an ordered list
of work packages — discrete delegations to specialist agents.

Standard specialist agents available:
- architecture_agent: Generates component diagrams, OpenAPI stubs, infrastructure plan
- backend_agent: Generates .NET CQRS services (commands, queries, handlers, migrations)
- frontend_agent: Generates Angular MFE (Nx workspace, components, routing, forms)
- database_agent: Generates EF Core migrations, RLS policies, seed data
- integration_agent: Generates MassTransit consumers, Saga state machines, BPMN flows
- devops_agent: Generates GitLab CI / Azure DevOps pipelines, Helm charts, Pulumi IaC
- qa_agent: Generates Playwright E2E tests, k6 load tests, Axe accessibility tests
- contract_test_agent: Generates Pact consumer/provider tests

AD Ports standard stack (enforce — do NOT suggest alternatives):
- Backend: .NET 9 + CQRS (MediatR, FluentValidation, EF Core, PostgreSQL)
- Frontend: Angular 20 MFE (Nx, Native Federation, PrimeNG 18, Tailwind, Transloco)
- Auth: Keycloak 25 + OpenFGA
- Messaging: MassTransit + RabbitMQ (or Kafka for high-throughput)
- Workflow: Camunda BPMN (for multi-step human workflows)
- Infrastructure: AKS + ArgoCD + Pulumi + Kong

Rules for decomposition:
1. architecture_agent ALWAYS runs first
2. database_agent runs BEFORE backend_agent (schema-first development)
3. backend_agent runs BEFORE frontend_agent (API-first development)
4. qa_agent and contract_test_agent run AFTER backend_agent and frontend_agent
5. devops_agent runs AFTER all code generation agents
6. Mark dependencies accurately — parallel agents must not depend on each other
7. Each work package is atomic — one agent, one bounded context or service
8. If a bounded context has both domain and infrastructure concerns, split into separate packages

Output ONLY valid JSON. No explanation text outside JSON.
```

---

## User Prompt Template

```
Project intent:
<intent>
{intent_json}
</intent>

Parsed BRD:
<brd>
{brd_json}
</brd>

Applicable standards and skills from Capability Fabric:
<standards>
{standards_json}
</standards>

Produce the work package decomposition:
{
  "decompositionRationale": "string — 2-3 sentences explaining key decomposition decisions",
  "servicesIdentified": [
    {
      "name": "string — PascalCase service name",
      "type": "backend|frontend|database|integration|infrastructure",
      "boundedContext": "string",
      "responsibilities": ["string"],
      "exposedInterfaces": ["string — e.g. 'REST /api/declarations'"],
      "consumedInterfaces": ["string — external systems or other services"]
    }
  ],
  "workPackages": [
    {
      "id": "WP-{NNN}",
      "agent": "architecture_agent|backend_agent|frontend_agent|database_agent|integration_agent|devops_agent|qa_agent|contract_test_agent",
      "title": "string — action phrase",
      "description": "string — what this agent must produce",
      "boundedContext": "string",
      "inputs": {
        "skills": ["string — skill IDs from Capability Fabric"],
        "specs": ["string — spec IDs"],
        "instructions": ["string — instruction IDs"],
        "artifacts_from": ["string — WP-NNN IDs this depends on"]
      },
      "expectedOutputs": ["string — list of artefacts this agent must produce"],
      "acceptanceCriteria": ["string — AC IDs from BRD that this WP addresses"],
      "dependsOn": ["string — WP-NNN IDs that must complete before this starts"],
      "canRunInParallelWith": ["string — WP-NNN IDs that can run simultaneously"],
      "estimatedComplexity": "LOW|MEDIUM|HIGH",
      "priority": 1
    }
  ]
}
```

---

## Example Input (Abbreviated)

```json
{
  "intent": {
    "projectName": "DGD — Dangerous Goods Declaration",
    "domain": "DGD",
    "boundedContexts": [
      { "name": "DeclarationSubmission", "keyOperations": ["submit", "validate", "approve"] },
      { "name": "FeeCalculation", "keyOperations": ["calculate_surcharge", "generate_invoice"] },
      { "name": "Notifications", "keyOperations": ["send_email", "send_sms"] }
    ],
    "externalIntegrations": [
      { "system": "SINTECE", "integrationType": "REST", "direction": "outbound" }
    ]
  },
  "brd": {
    "acceptanceCriteria": [
      { "id": "AC-DGD-001", "category": "integration" },
      { "id": "AC-DGD-002", "category": "functional" }
    ]
  }
}
```

---

## Example Output (Abbreviated)

```json
{
  "decompositionRationale": "DGD decomposes into three bounded contexts: DeclarationSubmission (core workflow + SINTECE integration), FeeCalculation (surcharge engine + invoicing), and Notifications (async fan-out). Architecture runs first to validate interface contracts; database schema precedes all backend generation.",

  "servicesIdentified": [
    {
      "name": "DeclarationService",
      "type": "backend",
      "boundedContext": "DeclarationSubmission",
      "responsibilities": ["DGD form submission", "SINTECE validation", "customs officer review workflow"],
      "exposedInterfaces": ["REST /api/declarations", "gRPC DeclarationEvents"],
      "consumedInterfaces": ["SINTECE REST API", "FeeService gRPC", "NotificationHub MQ"]
    }
  ],

  "workPackages": [
    {
      "id": "WP-001",
      "agent": "architecture_agent",
      "title": "Generate DGD Architecture Proposal",
      "description": "Generate component diagrams, sequence diagrams, OpenAPI stubs for all three bounded contexts, infrastructure plan",
      "boundedContext": "ALL",
      "inputs": {
        "skills": ["dotnet-cqrs-scaffold"],
        "specs": ["adports-keycloak-realm.schema.json", "adports-helm-chart.values.schema.json"],
        "instructions": ["coding-standards-csharp.md", "security-baseline.md"],
        "artifacts_from": []
      },
      "expectedOutputs": ["component-diagram.drawio", "sequence-diagrams/*.drawio", "openapi-stubs/*.yaml"],
      "acceptanceCriteria": ["AC-DGD-001", "AC-DGD-002"],
      "dependsOn": [],
      "canRunInParallelWith": [],
      "estimatedComplexity": "HIGH",
      "priority": 1
    },
    {
      "id": "WP-002",
      "agent": "database_agent",
      "title": "Generate Declaration Database Schema",
      "description": "EF Core migrations for declarations, fee_items, audit tables with RLS policies",
      "boundedContext": "DeclarationSubmission",
      "inputs": {
        "skills": ["dotnet-cqrs-scaffold"],
        "specs": [],
        "instructions": ["coding-standards-csharp.md"],
        "artifacts_from": ["WP-001"]
      },
      "expectedOutputs": ["Migrations/*.cs", "RLS policies SQL"],
      "acceptanceCriteria": [],
      "dependsOn": ["WP-001"],
      "canRunInParallelWith": [],
      "estimatedComplexity": "MEDIUM",
      "priority": 2
    }
  ]
}
```

---

## Validation Rules

- `workPackages` must include at least one `architecture_agent` package
- `architecture_agent` package must have `dependsOn: []` (always first)
- Every `backend_agent` package must depend on a `database_agent` package
- Every `frontend_agent` package must depend on a `backend_agent` package
- Every `qa_agent` package must depend on at least one `backend_agent` or `frontend_agent` package
- All `acceptanceCriteria` IDs must reference IDs present in the BRD input
- `estimatedComplexity` distribution should be realistic (not all HIGH)

---

*Work Package Decomposer Prompt — AD Ports AI Portal — v1.0 — Owner: Orchestrator Squad*
