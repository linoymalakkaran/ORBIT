# Phase 11 — Architecture Proposal & Review Workflow

## Summary

Implement the end-to-end architecture proposal generation and human review cycle. After the Orchestration Agent extracts intent and consults the capability fabric (Phase 10), this phase delivers the full proposal artifact set (draw.io diagrams, component decomposition, infrastructure plan, QA plan, security plan, Docusaurus spec site preview) and the review workflow (side-by-side diff, approval, revision tracking).

---

## Objectives

1. Implement the draw.io diagram generator (component, sequence, infrastructure diagrams).
2. Implement the component decomposition generator (bounded contexts → microservices).
3. Implement the OpenAPI stub generator (per service).
4. Implement the Docusaurus spec site preview generator.
5. Implement the infrastructure plan generator (AKS namespaces, Azure resources).
6. Implement the QA automation plan generator.
7. Implement the secure pipeline plan generator.
8. Implement the review workflow UI (rationale pane, diff viewer, comment thread).
9. Implement the revision loop (apply comments → regenerate → re-review).
10. Implement proposal versioning with the Pipeline Ledger.

---

## Duration

**3 weeks**

**Squad:** Orchestrator Squad (1 ML/AI engineer + 1 senior .NET + 1 Angular engineer)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | draw.io component diagram generator | Valid draw.io XML for a 5-service system |
| D2 | draw.io sequence diagram generator | Integration flows shown with correct actors |
| D3 | Component decomposition | Bounded contexts → services with responsibilities, interfaces |
| D4 | OpenAPI stub generator | Valid OpenAPI 3.1 YAML per service |
| D5 | Docusaurus spec site preview | Static HTML preview of architecture doc |
| D6 | Infrastructure plan | Helm chart skeleton + Pulumi resource list |
| D7 | QA automation plan | Playwright scenarios + load test targets per BRD story |
| D8 | Secure pipeline plan | Pipeline stages + security tool config per service |
| D9 | Review workflow UI | Diff viewer, rationale pane, comments, approve/reject/request-changes |
| D10 | Revision loop | Comments → new version → diff vs. previous; all versions in Ledger |

---

## Proposal Artifact Set

For a project like the DGD example, the proposal generates:

```
proposal/
├── v0.1/
│   ├── component-diagram.drawio        ← Architecture overview
│   ├── sequence-diagrams/
│   │   ├── dgd-submission-flow.drawio
│   │   ├── fee-calculation-flow.drawio
│   │   └── sintece-integration-flow.drawio
│   ├── component-decomposition.json    ← Structured service list
│   ├── openapi-stubs/
│   │   ├── declaration-service.yaml
│   │   ├── fee-service.yaml
│   │   └── notification-service.yaml
│   ├── infrastructure-plan.json        ← AKS + Azure resources
│   ├── qa-plan.json                    ← Playwright scenarios, k6 targets
│   ├── security-plan.json              ← Pipeline stages + SAST config
│   ├── architecture-doc.md             ← Docusaurus-ready markdown
│   └── jira-epics-draft.json          ← Initial epic + story decomposition
└── v0.2/                              ← After first revision
    └── ...  (diff from v0.1)
```

---

## draw.io Generator

The draw.io generator uses a template system:

```python
class DrawIOGenerator:
    COMPONENT_TEMPLATE = """
<mxGraphModel><root>
  <mxCell id="0"/><mxCell id="1" parent="0"/>
  {cells}
</root></mxGraphModel>
"""

    def generate_component_diagram(self, decomposition: ComponentDecomposition) -> str:
        cells = []
        x, y = 100, 100

        # Generate service boxes
        for i, service in enumerate(decomposition.services):
            cell_id = f"svc-{i}"
            x = 100 + (i % 4) * 250
            y = 100 + (i // 4) * 200
            cells.append(self._service_cell(cell_id, service, x, y))

        # Generate shared services
        for i, shared in enumerate(decomposition.shared_services):
            cells.append(self._shared_service_cell(f"shared-{i}", shared, ...))

        # Generate connections
        for dep in decomposition.dependencies:
            cells.append(self._edge_cell(dep.from_id, dep.to_id, dep.protocol))

        return self.COMPONENT_TEMPLATE.format(cells="\n  ".join(cells))

    def _service_cell(self, cell_id: str, service: Service, x: int, y: int) -> str:
        return f"""<mxCell id="{cell_id}" value="{service.name}"
          style="rounded=1;fillColor=#E8F0FE;strokeColor=#1A73E8;fontSize=12;"
          vertex="1" parent="1">
          <mxGeometry x="{x}" y="{y}" width="200" height="60" as="geometry"/>
        </mxCell>"""
```

The generator knows AD Ports stencils (shared Keycloak box, shared Notification Hub box, SINTECE external system box, AKS cluster boundary) from the `adports-drawio-stencils` spec.

---

## Component Decomposition

The component decomposition maps extracted intent to the standard AD Ports architecture patterns:

```python
STANDARD_PATTERNS = {
    "angular-mfe-dotnet-cqrs-postgres": ComponentPattern(
        frontend=["Angular MFE (Nx, Native Federation, PrimeNG)"],
        backend=["Command Service (.NET CQRS)", "Query Service (.NET CQRS)"],
        database=["PostgreSQL (EF Core migrations)"],
        messaging=["RabbitMQ (MassTransit)"],
        workflow=["Camunda BPMN (if workflow > 3 steps)"]
    )
}

def decompose_to_services(intent: Intent, pattern: str) -> ComponentDecomposition:
    """Map bounded contexts to concrete services using the selected pattern."""
    services = []
    for bc in intent.bounded_contexts:
        services.extend(instantiate_pattern(STANDARD_PATTERNS[pattern], bc))
    # Add shared services from AD Ports fabric
    services.extend(ALWAYS_INCLUDED_SHARED_SERVICES)
    return ComponentDecomposition(services=services, dependencies=infer_dependencies(services, intent))
```

---

## Review Workflow UI

The review surface shows the architect everything they need to approve or request changes:

```html
<!-- Review surface layout -->
<div class="review-container">
  <!-- Left: Artifact diff viewer -->
  <div class="artifact-panel">
    <adports-artifact-diff
      [leftVersion]="proposal.previousVersion"
      [rightVersion]="proposal.currentVersion"
      [artifactType]="selectedArtifact"
    />
  </div>

  <!-- Right: Rationale + approval -->
  <div class="review-panel">
    <!-- Orchestrator's reasoning -->
    <div class="rationale-pane p-4 bg-blue-50 rounded mb-4">
      <h3>Why these choices?</h3>
      <p>{{ proposal.rationale }}</p>
      <div class="skills-used text-sm text-gray-500">
        Based on: {{ proposal.skillsConsulted | join:', ' }}
      </div>
    </div>

    <!-- Comment thread -->
    <adports-comment-thread [comments]="proposal.comments" />

    <!-- Approval actions -->
    <div class="approval-actions mt-4">
      <p-button severity="success" label="Approve" (onClick)="approve()" />
      <p-button severity="warning" label="Request Changes" (onClick)="requestChanges()" />
      <p-button severity="danger" label="Reject" (onClick)="reject()" />
    </div>

    <!-- Execution estimate -->
    <div class="estimate-panel mt-4 text-sm">
      <span>Estimated execution: {{ proposal.estimate.duration }}</span>
      <span>Est. LLM cost: ${{ proposal.estimate.llmCost | number:'1.2-2' }}</span>
    </div>
  </div>
</div>
```

---

## Revision Loop

When an architect requests changes:

```
1. Architect submits: "Use shared jul-reference-data service for HS code lookup"
2. Portal:
   a. Stores revision request as Ledger event (portal.stage.proposal-revised with v0.1 hashes)
   b. Sends revision request to Orchestrator via Temporal signal
3. Orchestrator:
   a. Reads comment: identifies affected components (DGD declaration service, reference data service)
   b. Modifies component decomposition: replaces custom reference-data service with shared jul-reference-data
   c. Updates draw.io diagram: adds edge from declaration-service to jul-reference-data
   d. Updates OpenAPI stubs: removes /reference-data endpoint from declaration-service
   e. Generates new version (v0.2)
4. Portal:
   a. Stores v0.2 artifacts with hashes in Ledger
   b. Notifies architect: "Proposal updated to v0.2. Changes: removed custom reference-data service, added dependency on jul-reference-data"
5. Architect reviews diff (v0.1 vs v0.2) and approves
```

Every revision is stored as a separate set of artifacts with a new version number. The diff is computed server-side and cached.

---

## Step-by-Step Execution Plan

### Week 1: Diagram + Decomposition Generators

- [ ] Implement `DrawIOGenerator` with component + sequence diagram templates.
- [ ] Implement AD Ports stencil library in draw.io format.
- [ ] Implement `ComponentDecompositionGenerator` for standard patterns.
- [ ] Implement `OpenAPIStubGenerator` from component decomposition.
- [ ] Unit test: DGD-like intent → correct draw.io XML + OpenAPI stubs.

### Week 2: Plan Generators + Docusaurus

- [ ] Implement `InfrastructurePlanGenerator` (AKS namespaces + Pulumi resource list).
- [ ] Implement `QAPlanGenerator` (Playwright scenarios from BRD acceptance criteria).
- [ ] Implement `SecurePipelineGenerator` (GitLab CI/Azure DevOps pipeline stages).
- [ ] Implement `DocusaurusPreviewGenerator` (build static preview from markdown).
- [ ] Wire all generators into the `proposal_generation_node` from Phase 10.

### Week 3: Review Workflow UI + Revision Loop

- [ ] Implement review workflow UI (diff viewer, rationale, approval panel).
- [ ] Implement comment thread component with attributed comments.
- [ ] Implement revision loop (signal Temporal workflow, regenerate, produce diff).
- [ ] Implement proposal versioning in Ledger (each version = set of artifact hash entries).
- [ ] End-to-end test: DGD BRD → proposal → review comments → revision → approval.

---

## Gate Criterion (Gate 1 Prerequisite)

- Given the DGD BRD + HLD, orchestrator produces a complete proposal (all 8 artifact types) in < 10 minutes.
- Architect can review, comment, and request changes; orchestrator produces v0.2 in < 5 minutes.
- Architect approves; approval is signed and recorded in Pipeline Ledger with artifact hashes.
- draw.io diagrams are valid XML renderable in diagrams.net.
- OpenAPI stubs are valid YAML parseable by swagger-parser.

---

*Phase 11 — Architecture Proposal & Review Workflow — AI Portal — v1.0*
