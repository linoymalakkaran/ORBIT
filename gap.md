# ORBIT AI Portal — Implementation Gap Register

**Date:** 2026-04-29  
**Baseline:** `git log --oneline -5` shows `d4600e5` as HEAD  
**Purpose:** Sequenced execution plan for all deliverables missing from the plan-vs-implementation reverification.

---

## How to use this file

Each gap is an **atomic work item**. Items within the same group number can run in parallel. Groups must complete in order (each group depends on the previous).

> After completing each item, check it off and commit: `git commit -m "fix(gap-GXX): <description>"`

---

## Group 1 — Foundation Gaps (no dependencies)

These are foundational gaps in phases 02, 07, and 09 that block many later items. Implement all of Group 1 before moving to Group 2.

---

### G01 — Phase 02: OpenFGA Authorization Model Seeding

**Plan ref:** Phase 02, D2  
**Acceptance criterion:** All relationship tuples queryable; RBAC test suite passes  
**Gap:** `infra/k8s/openfga.yaml` deploys OpenFGA but no relationship tuples are seeded and no test suite exists.

**Files to create/edit:**
- `scripts/openfga-seed.sh` — CLI script using OpenFGA API to write all relationship tuples (users ↔ roles ↔ objects per Portal auth model)
- `src/portal-api/AdPorts.AiPortal.Tests/AuthorizationTests.cs` — xUnit test class that calls OpenFGA `Check` for each role/permission combination

**Implementation notes:**
- Model already defined in `infra/k8s/openfga.yaml` ConfigMap. Seed must target `http://openfga.ai-portal.svc:8080`
- Roles: `orbit-admin`, `architect`, `developer`, `qa`, `devops`, `pci-certified`
- Objects: `project`, `artifact`, `skill`, `ledger-entry`
- Tuples to seed: architect can `approve` project; developer can `read` project; developer cannot `approve` project

---

### G02 — Phase 02: Keycloak → OpenFGA Sync Service

**Plan ref:** Phase 02, D3  
**Acceptance criterion:** Keycloak group membership changes sync to OpenFGA within 30 seconds  
**Gap:** No sync service exists. Redis context works but group sync is absent.

**Files to create:**
- `src/portal-api/AdPorts.AiPortal.Infrastructure/Services/KeycloakOpenFgaSyncService.cs` — `IHostedService` that polls Keycloak `/admin/realms/ai-portal/groups` every 30s and calls OpenFGA Write API for changed tuples
- Register in `Program.cs` via `builder.Services.AddHostedService<KeycloakOpenFgaSyncService>()`

**Implementation notes:**
- Use `HttpClient` (named client `KeycloakAdmin`) for Keycloak admin API — credentials from Vault
- Use `HttpClient` (named client `OpenFGA`) for OpenFGA Write API at `http://openfga.ai-portal.svc:8080/stores/{OPENFGA_STORE_ID}/write`
- Record sync events to Pipeline Ledger (`event: keycloak_openfga_sync`)

---

### G03 — Phase 02: DbUp Migration Runner

**Plan ref:** Phase 02, D9  
**Acceptance criterion:** Runs idempotently on startup; version table maintained  
**Gap:** Only EF Core migrations exist. Plan requires DbUp for raw SQL scripts alongside EF Core.

**Files to create:**
- `src/portal-api/AdPorts.AiPortal.Infrastructure/Migrations/DbUp/001_initial_schema.sql` — initial raw SQL for any tables not covered by EF Core (audit log, raw event tables)
- `src/portal-api/AdPorts.AiPortal.Infrastructure/Services/DbUpMigrationRunner.cs` — uses `DbUp` NuGet to apply `*.sql` files from embedded resources on startup
- Add `DbUp` NuGet reference to `AdPorts.AiPortal.Infrastructure.csproj`
- Call `DbUpMigrationRunner.Run(connectionString)` early in `Program.cs` before EF Core migrations

---

### G04 — Phase 07: Instruction Library (10 docs)

**Plan ref:** Phase 07, D4  
**Acceptance criterion:** All instructions have owner, version, next-review date  
**Gap:** `src/capability-fabric/skills/` has 15 skills but `shared/instructions/` directory does not exist.

**Files to create** (all YAML front-matter + markdown body):
- `shared/instructions/coding-standards-csharp.md`
- `shared/instructions/coding-standards-typescript.md`
- `shared/instructions/api-design-guidelines.md`
- `shared/instructions/security-requirements.md`
- `shared/instructions/testing-strategy.md`
- `shared/instructions/ci-cd-standards.md`
- `shared/instructions/database-design-patterns.md`
- `shared/instructions/framework-lifecycle-policy.md`
- `shared/instructions/mpay-pci-dss-requirements.md`
- `shared/instructions/mpay-coding-standards.md`

**Each file must include this front-matter:**
```yaml
---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend", "devops"]
---
```

**Implementation notes:**
- `coding-standards-csharp.md` must include the 5 rules (CS001-CS006) referenced by the PR Review Agent
- `framework-lifecycle-policy.md` must match the policy constants in `src/fleet-upgrade-agent/app/main.py`
- `mpay-coding-standards.md` and `mpay-pci-dss-requirements.md` are required by the Phase 25 MPay domain pack

---

### G05 — Phase 07: Spec Library (8 specs)

**Plan ref:** Phase 07, D3  
**Acceptance criterion:** All specs valid JSON Schema / OpenAPI  
**Gap:** No `shared/specs/` or spec files exist anywhere in the repo.

**Files to create:**
- `shared/specs/project.schema.json` — JSON Schema for Portal Project entity
- `shared/specs/service.schema.json` — JSON Schema for registered Service entity
- `shared/specs/ledger-event.schema.json` — JSON Schema for Pipeline Ledger event
- `shared/specs/work-package.schema.json` — JSON Schema for Orchestrator work package
- `shared/specs/architecture-proposal.schema.json` — JSON Schema for architecture proposal artifact
- `shared/specs/vulnerability-finding.schema.json` — JSON Schema for Vulnerability Radar finding
- `shared/specs/openapi-stub.yaml` — OpenAPI 3.1 template stub used by Architecture Agent
- `shared/specs/domain-entity.schema.json` — base JSON Schema for generated domain entities

**Implementation notes:**
- All JSON Schemas must use `"$schema": "https://json-schema.org/draft/2020-12/schema"`
- `openapi-stub.yaml` must use OpenAPI 3.1 format with standard AD Ports error responses
- Fabric API must serve specs at `GET /api/fabric/specs` — update `src/capability-fabric/app/router.py`

---

### G06 — Phase 09: SonarQube MCP Server

**Plan ref:** Phase 09, D5  
**Acceptance criterion:** Quality gate status returned; analysis triggered  
**Gap:** `src/mcp-servers/` has no SonarQube MCP server.

**Files to create:**
- `src/mcp-servers/sonarqube-mcp/main.py` — FastAPI with 5 tools:
  - `get_quality_gate_status(project_key)` → `{status: "OK"|"ERROR", conditions: [...]}`
  - `trigger_analysis(project_key, branch)` → `{task_id, status}`
  - `get_issues(project_key, severities, resolved)` → `[{key, message, severity, component, line}]`
  - `get_metrics(project_key)` → `{coverage, duplications, bugs, vulnerabilities, code_smells}`
  - `configure_quality_gate(project_key, gate_name)` → `{success}`
- `src/mcp-servers/sonarqube-mcp/k8s/deployment.yaml`
- Environment prefix: `SONAR_`; env vars: `SONAR_URL`, `SONAR_TOKEN`

---

### G07 — Phase 09: Checkmarx MCP Server

**Plan ref:** Phase 09, D6  
**Acceptance criterion:** SAST scan triggered; findings returned  
**Gap:** No Checkmarx MCP server exists.

**Files to create:**
- `src/mcp-servers/checkmarx-mcp/main.py` — FastAPI with 5 tools:
  - `trigger_sast_scan(project_name, repo_url, branch)` → `{scan_id, status}`
  - `get_scan_results(scan_id)` → `{findings: [{id, severity, cwe_id, file, line, description}]}`
  - `get_project_last_scan(project_name)` → latest scan summary
  - `configure_preset(project_name, preset_name)` → `{success}`
  - `get_findings_by_severity(project_name, severity)` → filtered findings
- `src/mcp-servers/checkmarx-mcp/k8s/deployment.yaml`
- Environment prefix: `CHECKMARX_`; env vars: `CHECKMARX_URL`, `CHECKMARX_CLIENT_ID`, `CHECKMARX_CLIENT_SECRET`

---

### G08 — Phase 09: Draw.io MCP Server

**Plan ref:** Phase 09, D9  
**Acceptance criterion:** Architecture diagram generated from component list; exports working  
**Gap:** No Draw.io MCP server exists. The architecture-agent generates draw.io XML directly via LLM but there is no dedicated MCP tool for structured diagram operations.

**Files to create:**
- `src/mcp-servers/drawio-mcp/main.py` — FastAPI with 4 tools:
  - `generate_architecture_diagram(components, relationships, diagram_type)` → draw.io XML string
  - `generate_sequence_diagram(actors, messages)` → draw.io XML string
  - `export_diagram(xml, format)` → base64-encoded PNG/SVG (calls draw.io CLI or headless Electron)
  - `validate_diagram(xml)` → `{valid: bool, errors: [...]}`
- `src/mcp-servers/drawio-mcp/k8s/deployment.yaml`
- Environment prefix: `DRAWIO_`

---

### G09 — Phase 09: Newman/Postman MCP Server

**Plan ref:** Phase 09, D8  
**Acceptance criterion:** Collection run against staging; report returned  
**Gap:** No Newman MCP server exists.

**Files to create:**
- `src/mcp-servers/newman-mcp/main.py` — FastAPI with 6 tools:
  - `generate_collection(project_id, openapi_spec_url, environments)` → Postman Collection JSON
  - `run_collection(collection_id, environment, base_url)` → `{passed, failed, duration_ms, report_url}`
  - `get_run_report(run_id)` → detailed JUnit-format report
  - `upload_to_portal(run_id, project_id)` → posts results to Portal API
  - `list_collections(project_id)` → saved collections for a project
  - `get_environment(project_id, env_name)` → environment file with Vault-resolved secrets
- `src/mcp-servers/newman-mcp/k8s/deployment.yaml`
- Environment prefix: `NEWMAN_`

---

### G10 — Phase 09: Azure Boards / ADO MCP Server

**Plan ref:** Phase 09, D4  
**Acceptance criterion:** Work items created in Azure DevOps; hierarchy correct  
**Gap:** No Azure Boards MCP server exists (only Jira MCP exists).

**Files to create:**
- `src/mcp-servers/ado-mcp/main.py` — FastAPI with 6 tools:
  - `create_work_item(org, project, type, title, description, parent_id)` → `{id, url}`
  - `get_work_item(org, project, work_item_id)` → work item detail
  - `update_work_item(org, project, work_item_id, fields)` → `{success}`
  - `list_work_items(org, project, query)` → list matching work items (WIQL)
  - `create_pull_request(org, project, repo, source_branch, target_branch, title)` → `{pr_id, url}`
  - `transition_work_item(org, project, work_item_id, state)` → `{success}`
- `src/mcp-servers/ado-mcp/k8s/deployment.yaml`
- Environment prefix: `ADO_`; env vars: `ADO_ORG_URL`, `ADO_PAT`

---

## Group 2 — Agent Enhancement Gaps (depends on Group 1)

These gaps enhance existing agents and services. Group 1 must be complete (instructions + specs available, MCP servers running).

---

### G11 — Phase 07: Skill Quality Scorer

**Plan ref:** Phase 07, D7  
**Acceptance criterion:** Scores completeness, coverage, testability  
**Gap:** No scorer implemented in capability-fabric.

**Files to edit:**
- `src/capability-fabric/app/router.py` — add `GET /api/fabric/skills/{skill_id}/score` endpoint

**Implementation notes:**
- Score = weighted sum: completeness (40%) × coverage (35%) × testability (25%)
- Completeness: fields present out of required schema fields
- Coverage: number of use cases documented vs. expected minimum (3)
- Testability: presence of `examples` and `acceptance_criteria` fields
- Returns `{score: 0-100, grade: "A"|"B"|"C"|"F", breakdown: {...}}`

---

### G12 — Phase 11: Docusaurus Spec Site Preview

**Plan ref:** Phase 11, D5  
**Acceptance criterion:** Static HTML preview of architecture documentation  
**Gap:** Architecture agent generates draw.io XML and OpenAPI stubs but no Docusaurus static site preview.

**Files to edit:**
- `src/architecture-agent/app/main.py` — add `generate_spec_site` node to LangGraph pipeline after `generate_plans`

**Implementation notes:**
- Generate a `docusaurus.config.js` + `docs/` folder structure as a zip archive (base64-encoded in response)
- Spec site includes: component diagram (embedded draw.io SVG), OpenAPI spec (using `docusaurus-plugin-openapi-docs`), architecture decision records (ADRs), QA plan, security plan
- Store generated site zip as artifact in `POST /api/proposals` response under `spec_site_zip`
- Add `GET /api/proposals/{project_id}/spec-site` endpoint to download zip

---

### G13 — Phase 14: Camunda BPMN Generator

**Plan ref:** Phase 14, D9  
**Acceptance criterion:** Valid `.bpmn` XML deployed to Camunda; process starts correctly  
**Gap:** Database agent has no BPMN generation capability.

**Files to edit:**
- `src/database-agent/app/main.py` — add `POST /api/generate/workflow` endpoint

**Implementation notes:**
- Input: `{process_name, steps: [{name, type: "user_task|service_task|exclusive_gateway|parallel_gateway", assignee?, form_key?}], variables: [...]}`
- Output: valid BPMN 2.0 XML using LLM with strict XML schema prompt + Camunda 8 extensions
- Include: start event, end event, all task nodes, sequence flows with correct `bpmn:` namespace
- Also generate Camunda deploy script: `curl POST /zeebe/api/v1/deployments` with `multipart/form-data`
- Validate generated XML has `<bpmn:definitions xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL">`

---

### G14 — Phase 15: Azure DevOps Pipeline Generator

**Plan ref:** Phase 15, D2  
**Acceptance criterion:** ADO pipeline stages pass for DGD service (build → test → scan → deploy-dev)  
**Gap:** DevOps agent only generates GitLab CI. No Azure Pipelines YAML generator.

**Files to edit:**
- `src/devops-agent/app/main.py` — add `generate_azure_devops_pipeline` LangGraph node

**Implementation notes:**
- Input: `{service_name, language: "dotnet"|"angular"|"python", runs_on: "ubuntu-latest"}`
- Output: `azure-pipelines.yml` with stages matching the GitLab CI structure:
  - `stages: [lint, test, security-scan, build, trivy-scan, deploy-dev, deploy-prod]`
  - Uses `microsoft/dotnet-sdk:9.0` pool for .NET; `node:22-alpine` for Angular
  - SonarQube task via `SonarQubePrepare@5` + `SonarQubeAnalyze@5` + `SonarQubePublish@5`
  - Trivy via bash task `trivy image --exit-code 1 --severity CRITICAL`
  - Deploy via `HelmDeploy@0` task to TKG kubeconfig stored in ADO service connection
- Add `azure_pipeline_yaml` field to `DevOpsGenState` and `DevOpsGenResponse`
- Add to `POST /api/generate/devops` request: `pipeline_provider: "gitlab"|"azure_devops"|"both"`

---

### G15 — Phase 15: Pulumi IaC Output from DevOps Agent

**Plan ref:** Phase 15, D3  
**Acceptance criterion:** `pulumi up` creates resources (PostgreSQL DB, Storage Account / MinIO bucket, Service Bus topic)  
**Gap:** DevOps agent generates Helm/Kong/ArgoCD but no Pulumi IaC for service-level Azure or on-prem resources.

**Files to edit:**
- `src/devops-agent/app/main.py` — add `generate_pulumi_iac` LangGraph node (between `generate_argocd_app` and `generate_security_configs`)

**Implementation notes:**
- Input: `{service_name, needs_database: bool, needs_storage: bool, needs_servicebus: bool}`
- Output: TypeScript Pulumi program for `src/infrastructure/k8s/` stack:
  - PostgreSQL: `new k8s.core.v1.ConfigMap` + Secret referencing Vault for DSN
  - MinIO bucket: `new k8s.apiextensions.CustomResource` for MinIO Bucket CRD (operator-managed)
  - RabbitMQ topic: `new k8s.apiextensions.CustomResource` for RabbitmqCluster CRD exchange definition
- Add `pulumi_iac_ts` field to `DevOpsGenState`
- Store generated IaC in `src/infrastructure/k8s/services/{service_name}.ts`

---

### G16 — Phase 17: WireMock Harness Generator

**Plan ref:** Phase 17, D6  
**Acceptance criterion:** SINTECE external service mocked; integration flow passes  
**Gap:** Integration test agent generates Postman/Newman but no WireMock configuration.

**Files to edit:**
- `src/integration-test-agent/app/main.py` — add `generate_wiremock_config` LangGraph node after `generate_test_data`

**Implementation notes:**
- Input: `{external_service_name, openapi_spec: str}` — spec can be provided or fetched from capability fabric
- Output: WireMock stub JSON files: `mappings/` directory with one file per endpoint
- Each stub: `{"request": {"method": "POST", "url": "/api/v2/..."}, "response": {"status": 200, "jsonBody": {...}}}`
- Also generate `docker-compose.wiremock.yml` with `wiremock/wiremock:3.5.4` image mounting `mappings/` volume
- Add `wiremock_mappings` and `wiremock_compose` to response model

---

### G17 — Phase 19: Registry MCP Server

**Plan ref:** Phase 19, D10  
**Acceptance criterion:** 5 MCP tools callable from Orchestrator agents  
**Gap:** Project Registry has a REST API but no MCP server wrapping it.

**Files to create:**
- `src/mcp-servers/registry/main.py` — already has directory; implement 5 tools:
  - `get_project(project_id)` → project detail with services list
  - `list_services(framework?, environment?)` → services matching filters
  - `get_dependency_graph(project_id)` → nodes + edges JSON
  - `get_framework_inventory()` → all services with versions + compliance status
  - `register_service(project_id, service_name, framework, version, repo_url)` → `{service_id}`
- `src/mcp-servers/registry/k8s/deployment.yaml`
- Register in `src/mcp-servers/registry/seed.json` — add to MCP registry on startup

---

### G18 — Phase 19: Auto-Registration from Architecture Approval

**Plan ref:** Phase 19, D2  
**Acceptance criterion:** Approval of architecture proposal auto-creates Registry entry  
**Gap:** Architecture approval in portal-api does not call project-registry.

**Files to edit:**
- `src/portal-api/AdPorts.AiPortal.Application/Approvals/ApproveArtifactCommandHandler.cs` — after setting status to `Approved`, call `IProjectRegistryClient.RegisterProject(...)` if artifact type is `ArchitectureProposal`
- Create `src/portal-api/AdPorts.AiPortal.Infrastructure/Clients/ProjectRegistryClient.cs` — typed `HttpClient` calling `http://project-registry.ai-portal.svc:80/api/registry/projects`

---

### G19 — Phase 22: BA Agent Jira/ADO Sync

**Plan ref:** Phase 22, D4 + D6  
**Acceptance criterion:** Epics + stories created in Jira; hierarchy correct; human review gate before sync  
**Gap:** BA agent generates stories as JSON but never calls Jira MCP or ADO MCP.

**Files to edit:**
- `src/ba-agent/app/main.py` — add 2 new endpoints:
  - `POST /api/review` — stores generated stories in memory with `status: "pending_review"`, returns review ID
  - `POST /api/sync-to-jira` — accepts `{review_id, jira_project_key, jira_mcp_url}`, calls Jira MCP `create_work_item` for each epic + story
  - `POST /api/sync-to-ado` — same but via ADO MCP `create_work_item`
- Add `status` field (`pending_review | approved | synced`) to the in-memory story store
- Record sync events to Pipeline Ledger

**Implementation notes:**
- Stories must be synced in order: create epic first → get epic ID → create stories with `parent_id = epic_id`
- Story format for Jira: `{type: "Story", summary: "...", description: "...", story_points: N, acceptance_criteria: "..."}`
- Human review gate: `POST /api/review` returns review URL; sync blocked until `PATCH /api/review/{id}/approve`

---

### G20 — Phase 22: Ticket Transition to "In Review"

**Plan ref:** Phase 22, D10  
**Acceptance criterion:** Ticket transitions to "In Review" when PR is opened  
**Gap:** Ticket agent creates PR but never transitions the source Jira/ADO ticket.

**Files to edit:**
- `src/ticket-agent/app/main.py` — in `create_branch_and_pr` node, after MR creation succeeds, call:
  - `POST {jira_mcp_url}/tools/transition_issue` with `{"issue_key": ticket_id, "transition": "In Review"}`
  - OR `POST {ado_mcp_url}/tools/transition_work_item` with `{"work_item_id": ticket_id, "state": "In Review"}`
- Add `jira_ticket_id` and `ado_work_item_id` fields to `TicketImplRequest` and `TicketImplState`

---

## Group 3 — Phase 25 Ecosystem Gaps (depends on Groups 1 + 2)

These are the largest remaining gaps. Groups 1 and 2 must be complete before starting Group 3 (domain packs consume the instruction library from G04 and the spec library from G05).

---

### G21 — Phase 25: MPay Domain Agent Pack

**Plan ref:** Phase 25, D1  
**Acceptance criterion:** Payment service generated; PCI-DSS hooks active; sandbox payment processed  
**Gap:** No MPay domain pack exists.

**Files to create:**
- `src/domain-packs/mpay/pack.py` — `DomainPack` definition with:
  - Skills: `mpay-payment-gateway-integration`, `mpay-pci-dss-scoping`, `mpay-reconciliation-workflow`, `mpay-chargeback-handling`
  - Instructions: `mpay-coding-standards`, `mpay-pci-dss-requirements` (created in G04)
  - Stencils: references to `mpay-pci-dss-zones.drawio.stencil`
- `src/domain-packs/mpay/stencils/mpay-pci-dss-zones.drawio.stencil` — draw.io stencil XML for PCI-DSS network zones (cardholder data environment, DMZ, external)
- `src/domain-packs/mpay/skills/mpay-payment-gateway-integration.yaml` — Capability Fabric skill YAML
- `src/domain-packs/mpay/skills/mpay-pci-dss-scoping.yaml`
- `src/domain-packs/mpay/skills/mpay-reconciliation-workflow.yaml`
- `src/domain-packs/mpay/skills/mpay-chargeback-handling.yaml`
- `src/domain-packs/mpay/k8s/deployment.yaml` — k8s registration job that seeds skills into capability-fabric on startup
- `src/domain-packs/mpay/tests/test_mpay_pack.py`

---

### G22 — Phase 25: CRM/CMS Domain Agent Pack

**Plan ref:** Phase 25, D2  
**Acceptance criterion:** Customer journey MFE generated; CMS content type scaffold works  
**Gap:** No CRM/CMS domain pack exists.

**Files to create:**
- `src/domain-packs/crm-cms/pack.py`
- `src/domain-packs/crm-cms/skills/crm-customer-journey.yaml`
- `src/domain-packs/crm-cms/skills/cms-content-type-scaffold.yaml`
- `src/domain-packs/crm-cms/skills/crm-lead-management.yaml`
- `src/domain-packs/crm-cms/k8s/deployment.yaml`
- `src/domain-packs/crm-cms/tests/test_crm_cms_pack.py`

---

### G23 — Phase 25: ERP Domain Agent Pack

**Plan ref:** Phase 25, D3  
**Acceptance criterion:** Oracle integration scaffold; PO approval workflow; BizTalk replacement option  
**Gap:** No ERP domain pack exists.

**Files to create:**
- `src/domain-packs/erp/pack.py`
- `src/domain-packs/erp/skills/erp-oracle-integration.yaml`
- `src/domain-packs/erp/skills/erp-purchase-order-workflow.yaml`
- `src/domain-packs/erp/skills/erp-biztalk-replacement.yaml`
- `src/domain-packs/erp/templates/oracle-purchase-order.scriban` — .NET Scriban template for Oracle EBS PO integration
- `src/domain-packs/erp/k8s/deployment.yaml`
- `src/domain-packs/erp/tests/test_erp_pack.py`

---

### G24 — Phase 25: JUL Domain Agent Pack

**Plan ref:** Phase 25, D4  
**Acceptance criterion:** JUL-specific stencils in draw.io generator; SINTECE V2 integration harness  
**Gap:** No JUL domain pack exists.

**Files to create:**
- `src/domain-packs/jul/pack.py`
- `src/domain-packs/jul/skills/jul-logistics-patterns.yaml`
- `src/domain-packs/jul/skills/sintece-v2-integration.yaml`
- `src/domain-packs/jul/stencils/jul-logistics.drawio.stencil` — draw.io stencil for logistics flow diagrams
- `src/domain-packs/jul/wiremock/sintece-v2-stubs.json` — WireMock stub for SINTECE V2 external service
- `src/domain-packs/jul/k8s/deployment.yaml`
- `src/domain-packs/jul/tests/test_jul_pack.py`

---

### G25 — Phase 25: PCS Domain Agent Pack

**Plan ref:** Phase 25, D5  
**Acceptance criterion:** Vessel scheduling domain model; berth management service scaffold  
**Gap:** No PCS domain pack exists.

**Files to create:**
- `src/domain-packs/pcs/pack.py`
- `src/domain-packs/pcs/skills/pcs-vessel-scheduling.yaml`
- `src/domain-packs/pcs/skills/pcs-berth-management.yaml`
- `src/domain-packs/pcs/skills/pcs-port-community-system.yaml`
- `src/domain-packs/pcs/stencils/pcs-vessel-diagrams.drawio.stencil`
- `src/domain-packs/pcs/k8s/deployment.yaml`
- `src/domain-packs/pcs/tests/test_pcs_pack.py`

---

### G26 — Phase 25: vLLM Deployment (replace Ollama for production)

**Plan ref:** Phase 25, D6  
**Acceptance criterion:** Llama 3.3 70B running on TKG GPU nodes via vLLM; `/health` endpoint responds  
**Gap:** Current `infra/sovereign-ai/llama-deployment.yaml` uses Ollama. Plan specifies vLLM with OpenAI-compatible API at port 8000.

**Files to edit:**
- `infra/sovereign-ai/llama-deployment.yaml` — replace Ollama image with `vllm/vllm-openai:v0.5.5`
  - Container command: `["python", "-m", "vllm.entrypoints.openai.api_server", "--model", "meta-llama/Llama-3.3-70B-Instruct", "--port", "8000", "--tensor-parallel-size", "1"]`
  - Port: 8000 (OpenAI-compatible)
  - readinessProbe: `GET /health` (vLLM) instead of `GET /api/tags` (Ollama)
  - Resources: 8-16 CPU, 80-120Gi RAM, `nvidia.com/gpu: "1"`
  - InitContainer: download model from HuggingFace hub (requires `HF_TOKEN` from Vault)
- `infra/litellm/deployment.yaml` — update `llama3-70b-sovereign` model config:
  - Change `api_base` from `http://llama-inference.sovereign-ai.svc:11434` to `http://llama-inference.sovereign-ai.svc:8000`
  - Change `custom_llm_provider` from `ollama` to `openai`

**Files to create:**
- `src/infrastructure/stacks/tanzu/sovereign-ai.ts` — Pulumi stack for GPU node provisioning (from plan code snippet)

---

### G27 — Phase 25: Intelligent LLM Routing

**Plan ref:** Phase 25, D7  
**Acceptance criterion:** HIGH-sensitivity tasks → sovereign; STANDARD → cloud; ECONOMY → DeepSeek  
**Gap:** No sensitivity-based routing exists in orchestrator or guardrails. LiteLLM config has models but no automatic tier selection based on data classification.

**Files to create:**
- `src/orchestrator/app/llm_router.py` — `IntelligentLLMRouter` class with routing table:
  ```python
  ROUTING_TABLE = {
      ("HIGH",     "CLASSIFIED"): "llama3-70b-sovereign",
      ("HIGH",     "INTERNAL"):   "gpt-4o",
      ("HIGH",     "PUBLIC"):     "gpt-4o",
      ("STANDARD", "CLASSIFIED"): "llama3-70b-sovereign",
      ("STANDARD", "INTERNAL"):   "gpt-4o-mini",
      ("STANDARD", "PUBLIC"):     "gpt-4o-mini",
      ("ECONOMY",  "CLASSIFIED"): "llama3-70b-sovereign",
      ("ECONOMY",  "INTERNAL"):   "gpt-4o-mini",
      ("ECONOMY",  "PUBLIC"):     "gpt-4o-mini",
  }
  ```

**Files to edit:**
- `src/orchestrator/app/graph.py` — replace direct `litellm.acompletion` calls with `IntelligentLLMRouter.route(sensitivity, classification)` to select model
- `src/orchestrator/app/config.py` — add `data_classification: str = "INTERNAL"` and `task_sensitivity: str = "STANDARD"` settings
- `infra/litellm/deployment.yaml` — verify `deepseek/deepseek-chat` model entry exists for ECONOMY tier

---

## Execution Sequence Summary

```
Group 1 (parallel within group, no dependencies):
  G01  Phase 02 — OpenFGA tuple seeding + RBAC tests
  G02  Phase 02 — Keycloak → OpenFGA sync service
  G03  Phase 02 — DbUp migration runner
  G04  Phase 07 — shared/instructions/ library (10 docs)
  G05  Phase 07 — shared/specs/ library (8 specs)
  G06  Phase 09 — SonarQube MCP server
  G07  Phase 09 — Checkmarx MCP server
  G08  Phase 09 — Draw.io MCP server
  G09  Phase 09 — Newman/Postman MCP server
  G10  Phase 09 — Azure Boards / ADO MCP server

Group 2 (depends on Group 1 being complete):
  G11  Phase 07 — Skill quality scorer
  G12  Phase 11 — Docusaurus spec site preview
  G13  Phase 14 — Camunda BPMN generator
  G14  Phase 15 — Azure DevOps pipeline generator
  G15  Phase 15 — Pulumi IaC output from DevOps agent
  G16  Phase 17 — WireMock harness generator
  G17  Phase 19 — Registry MCP server
  G18  Phase 19 — Auto-registration from architecture approval
  G19  Phase 22 — BA agent Jira/ADO sync + human review gate
  G20  Phase 22 — Ticket transition to "In Review"

Group 3 (depends on Groups 1 + 2 — especially G04 + G05):
  G21  Phase 25 — MPay domain agent pack
  G22  Phase 25 — CRM/CMS domain agent pack
  G23  Phase 25 — ERP domain agent pack
  G24  Phase 25 — JUL domain agent pack
  G25  Phase 25 — PCS domain agent pack
  G26  Phase 25 — vLLM deployment (replace Ollama)
  G27  Phase 25 — Intelligent LLM routing
```

---

## Commit Convention

Use this commit message prefix for each gap item:

```
fix(gap-G01): Phase 02 — OpenFGA tuple seeding + RBAC test suite
fix(gap-G04): Phase 07 — add shared/instructions/ library (10 docs)
fix(gap-G06): Phase 09 — SonarQube MCP server (5 tools)
```

---

## Files Not Required

The following plan deliverables are intentionally deferred (documented separately or handled operationally):

- **Phase 01 D12** — Day-2 runbooks → `docs/runbooks/` directory (operational docs, not code)
- **Phase 07 D8** — Scheduled review cadence → cron job in ArgoCD, out of scope for code gaps
- **Phase 20 D4** — Business metrics monitor → requires integration with live AD Ports KPI systems (deferred to production)
- **Phase 25 D8/D9** — NESA/SOC-2 automated evidence → `docs/COMPLIANCE.md` already created; full automation requires access to live audit systems

---

*Generated: 2026-04-29 | Total gap items: 27 | Groups: 3*
