# Phase 25 — Ecosystem Agents, Scale & Sovereignty (Gate 4 Checkpoint)

## Summary

The final phase delivers three outcomes: (1) **Ecosystem Agents** for the remaining AD Ports business domains (MPay, CRM, CMS, ERP, JUL, PCS), (2) **Scale hardening** to handle the full AD Ports workload (20+ concurrent projects, 50+ developer teams), and (3) **Sovereign AI deployment** for classified workloads using self-hosted Llama 3.3 70B on GPU nodes, with NESA UAE cybersecurity compliance and SOC-2 Type II readiness.

---

## Objectives

1. Implement MPay domain agent pack (payment gateway, reconciliation, PCI-DSS compliance hooks).
2. Implement CRM/CMS domain agent pack (customer journey, content management).
3. Implement ERP domain agent pack (Oracle integration, PO/GR workflow, approval chains).
4. Implement JUL domain agent pack (Jebel Ali logistics-specific patterns + SINTECE V2).
5. Implement PCS domain agent pack (Port Community System, vessel scheduling, berth management).
6. Implement sovereign AI deployment (Llama 3.3 70B on AKS GPU nodes, AzureML or vLLM).
7. Implement intelligent LLM cost routing (sovereign tier for HIGH sensitivity, cloud for standard).
8. Implement NESA UAE cybersecurity compliance checks (automated audit evidence).
9. Implement SOC-2 Type II evidence collection automation.
10. Conduct Gate 4 validation — the platform goes to full production for all AD Ports domains.

---

## Prerequisites

- Phases 1–24 complete and Gate 3 passed.
- AKS GPU node pool provisioned (Phase 01 extension).
- NESA compliance framework documented.
- AD Ports legal/compliance team signed off on sovereign AI policy.

---

## Duration

**6 weeks** (last week = Gate 4 validation + production go-live)

**Squad:** All squads — coordinated by Platform Squad lead. Governance Squad leads NESA/SOC-2. Intelligence Squad leads sovereign AI.

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | MPay agent pack | Payment service generated; PCI-DSS hooks active; sandbox payment processed |
| D2 | CRM/CMS agent pack | Customer journey MFE generated; CMS content type scaffold works |
| D3 | ERP agent pack | Oracle integration scaffold; PO approval workflow; BizTalk replacement option |
| D4 | JUL agent pack | JUL-specific stencils in draw.io generator; SINTECE V2 integration harness |
| D5 | PCS agent pack | Vessel scheduling domain model; berth management service scaffold |
| D6 | Sovereign AI | Llama 3.3 70B running on AKS GPU nodes; vLLM endpoint health checked |
| D7 | Intelligent routing | HIGH-sensitivity tasks → sovereign; STANDARD → cloud; ECONOMY → DeepSeek |
| D8 | NESA compliance | 85% of NESA controls have automated evidence collection |
| D9 | SOC-2 evidence | All required SOC-2 evidence types collected and stored |
| D10 | Gate 4 validation | Full Gate 4 checklist passes; platform in production |

---

## Domain Agent Packs

Each domain agent pack extends the generic specialist agents with domain-specific:
- **Stencils** — domain-specific draw.io stencils (MPay PCI-DSS zones, PCS vessel diagrams).
- **Skills** — domain-specific skills in the Capability Fabric.
- **Templates** — code templates tuned for the domain's typical patterns.
- **Instructions** — AI tool instructions with domain-specific rules.
- **Specs** — JSON schemas for domain entities.
- **Integration harnesses** — WireMock/Pact for the domain's external integrations.

### MPay Domain Agent Pack

```python
# domain_packs/mpay/mpay_pack.py
MPAY_EXTENSIONS = DomainPack(
    name="mpay",
    skills=[
        "mpay-payment-gateway-integration",
        "mpay-pci-dss-scoping",
        "mpay-reconciliation-workflow",
        "mpay-chargeback-handling",
    ],
    instructions=["mpay-coding-standards", "mpay-pci-dss-requirements"],
    stencils=["mpay-pci-dss-zones.drawio.stencil"],
    forbidden_operations=[
        "store_full_pan_in_database",    # PCI-DSS: No full PANs
        "log_card_data",                 # PCI-DSS: No card data in logs
        "unencrypted_transmission",      # PCI-DSS: TLS everywhere
    ],
    external_integrations=[
        ExternalIntegration("mpay-gateway", "https://api.mpay.ae/v2", WireMockHarness("mpay-wiremock")),
        ExternalIntegration("uaepass", "https://id.uaepass.ae", WireMockHarness("uaepass-wiremock")),
    ]
)
```

### ERP Integration Hook

```python
# domain_packs/erp/oracle_integration.py
ERP_ORACLE_PATTERNS = [
    # Oracle E-Business Suite integration patterns
    TemplatePattern(
        name="oracle-purchase-order",
        description="PO creation/approval flow with Oracle EBS",
        backend_template="erp-po-service.dotnet.scriban",
        oracle_tables=["PO_HEADERS_ALL", "PO_LINES_ALL", "PO_DISTRIBUTIONS_ALL"],
        approval_workflow="oracle-po-approval.bpmn"
    ),
    TemplatePattern(
        name="oracle-goods-receipt",
        description="GR posting to Oracle inventory",
        backend_template="erp-gr-service.dotnet.scriban",
        oracle_tables=["RCV_TRANSACTIONS", "MTL_MATERIAL_TRANSACTIONS"]
    ),
]
```

---

## Sovereign AI Deployment

### vLLM on AKS GPU Nodes

```yaml
# pulumi/sovereign-ai.ts — GPU node pool + vLLM deployment
const gpuNodePool = new azure.containerservice.AgentPool("sovereign-ai-gpu", {
    resourceGroupName: "adports-aks-rg",
    resourceName: aksCluster.name,
    agentPoolName: "gpupool",
    vmSize: "Standard_NC4as_T4_v3",  // T4 GPU, 4 vCPU, 28 GB RAM
    count: 2,
    mode: "User",
    nodeTaints: ["sku=gpu:NoSchedule"],
    nodeLabels: { "workload": "sovereign-ai" },
    osSku: azure.containerservice.OSSku.Ubuntu,
});
```

```yaml
# helm/vllm/values.yaml
image:
  repository: vllm/vllm-openai
  tag: v0.5.5

model:
  name: "meta-llama/Llama-3.3-70B-Instruct"
  quantization: "awq"          # 4-bit quantization to fit on T4
  maxModelLen: 16384
  gpuMemoryUtilization: 0.90

resources:
  requests:
    nvidia.com/gpu: 1
  limits:
    nvidia.com/gpu: 1

tolerations:
  - key: "sku"
    operator: "Equal"
    value: "gpu"
    effect: "NoSchedule"

auth:
  keycloakEnabled: true
  requiredRoles: ["ai-portal-sovereign"]
```

### Intelligent LLM Routing

```python
# orchestration/llm_router.py
class IntelligentLLMRouter:
    """
    Routes LLM calls to the appropriate tier based on:
    - Task sensitivity (HIGH/STANDARD/ECONOMY)
    - Data classification (CLASSIFIED/INTERNAL/PUBLIC)
    - Cost budget remaining
    - Sovereign mode setting (per project or per org)
    """

    ROUTING_TABLE = {
        # (sensitivity, data_classification) → LLM tier
        ("HIGH",     "CLASSIFIED"): "sovereign",  # Self-hosted Llama 3.3 70B
        ("HIGH",     "INTERNAL"):   "premium",    # Claude Sonnet 4.x
        ("HIGH",     "PUBLIC"):     "premium",
        ("STANDARD", "CLASSIFIED"): "sovereign",
        ("STANDARD", "INTERNAL"):   "standard",   # Azure OpenAI GPT-4o
        ("STANDARD", "PUBLIC"):     "standard",
        ("ECONOMY",  "CLASSIFIED"): "sovereign",
        ("ECONOMY",  "INTERNAL"):   "economy",    # DeepSeek-V3
        ("ECONOMY",  "PUBLIC"):     "economy",
    }

    async def route(self, request: LLMRequest, context: ProjectContext) -> LLMTier:
        sensitivity = await self._classify_task_sensitivity(request.task_type)
        data_classification = context.data_classification

        tier = self.ROUTING_TABLE.get((sensitivity, data_classification), "standard")

        # Override: if project has sovereign_mode=True, force all to sovereign
        if context.sovereign_mode:
            tier = "sovereign"

        # Budget check: if standard budget exhausted, downgrade to economy
        if tier == "standard" and context.standard_budget_remaining < 0:
            tier = "economy"

        return LLMTier(tier=tier, model=TIER_MODELS[tier])
```

---

## NESA Compliance Automation

```python
# governance/nesa_compliance.py
NESA_CONTROLS = [
    NesaControl(
        id="NESA-IAM-001",
        title="Multi-factor authentication for privileged access",
        evidence_source="keycloak_mfa_enforcement",
        automated=True,
        evidence_query=lambda: keycloak_mcp.get_realm_mfa_policy()
    ),
    NesaControl(
        id="NESA-LOG-001",
        title="All access to critical systems must be logged",
        evidence_source="pipeline_ledger",
        automated=True,
        evidence_query=lambda: ledger.get_summary_stats(last_days=30)
    ),
    NesaControl(
        id="NESA-CRYPT-001",
        title="Encryption at rest for sensitive data",
        evidence_source="aks_storage_encryption",
        automated=True,
        evidence_query=lambda: aks_mcp.get_storage_encryption_status()
    ),
    NesaControl(
        id="NESA-VM-001",
        title="Vulnerability management — patch within 30 days",
        evidence_source="vulnerability_radar",
        automated=True,
        evidence_query=lambda: vulnerability_radar.get_remediation_sla_report()
    ),
    # ... 40+ more controls
]

async def collect_compliance_evidence() -> NesaComplianceReport:
    results = []
    for control in NESA_CONTROLS:
        if control.automated:
            evidence = await control.evidence_query()
            results.append(ControlResult(
                control=control,
                status="PASS" if evidence.compliant else "FAIL",
                evidence=evidence.data,
                collected_at=datetime.utcnow()
            ))
    return NesaComplianceReport(controls=results, generated_at=datetime.utcnow())
```

---

## Gate 4 Criteria (Full Production)

| # | Criterion | Measurement |
|---|-----------|------------|
| G4.1 | Platform live for all 6 AD Ports domains (DGD/MPay/CRM/CMS/ERP/JUL/PCS) | Registry domain count |
| G4.2 | Sovereign AI processing HIGH-sensitivity tasks (no data to cloud) | LLM routing audit log |
| G4.3 | NESA compliance score ≥ 85% (automated evidence) | NESA report |
| G4.4 | SOC-2 Type II readiness documented | Evidence package |
| G4.5 | 20 concurrent projects supported without degradation | k6 platform load test |
| G4.6 | 50+ developer teams onboarded | User count in Keycloak |
| G4.7 | Time to first deployable service < 4 hours (any new project) | Stopwatch on Ledger |
| G4.8 | All previous Gate criteria (1–3) still passing | Full regression run |
| G4.9 | Zero P0 vulnerabilities in production | Vulnerability Radar |
| G4.10 | Pipeline Ledger chain integrity 100% (all events signed) | Tamper-detection check |
| G4.11 | Monthly Azure cost < $8,000 for full production platform | Azure Cost Management |
| G4.12 | Developer NPS score ≥ 40 (surveyed from 50+ users) | Survey results |

---

## Step-by-Step Execution Plan

### Weeks 1–2: Domain Agent Packs

- [ ] Implement MPay domain pack (stencils, skills, PCI-DSS hooks, payment gateway harness).
- [ ] Implement JUL domain pack (logistics stencils, SINTECE V2 harness).
- [ ] Implement PCS domain pack (vessel scheduling domain model, berth management).
- [ ] Implement ERP domain pack (Oracle integration templates, PO/GR workflows).
- [ ] Implement CRM/CMS domain pack (customer journey, content management).

### Week 3: Sovereign AI Deployment

- [ ] Provision GPU node pool in AKS (Pulumi, T4 GPU, 2 nodes).
- [ ] Deploy vLLM with Llama 3.3 70B (AWQ quantized).
- [ ] Implement intelligent LLM routing (routing table + budget check).
- [ ] Test: CLASSIFIED data → routed to sovereign; never sent to cloud LLM.

### Week 4: NESA + SOC-2 Automation

- [ ] Implement NESA control evidence collection for all 40+ controls.
- [ ] Implement SOC-2 evidence collection (access logs, change management, incident response).
- [ ] Implement compliance report generator (PDF export from Portal).
- [ ] Test: NESA report scores ≥ 85%.

### Week 5: Scale Hardening

- [ ] Implement Orchestrator horizontal scaling (HPA, min 3, max 20 replicas).
- [ ] Implement rate limiting per team (quota management in Hook Engine).
- [ ] Implement multi-tenant isolation (each squad's work isolated in separate namespace + RBAC).
- [ ] Load test: 20 concurrent projects, 50 concurrent users.

### Week 6: Gate 4 Validation + Go-Live

- [ ] Run full Gate 4 validation checklist.
- [ ] Fix any issues found.
- [ ] Record Gate 4 pass in Pipeline Ledger with all 12 criteria signed.
- [ ] Platform goes live for all AD Ports domains.
- [ ] Handover to Platform Squad for ongoing operations.

---

## Post-Phase 25: Ongoing Operations

After Gate 4:
- **Monthly**: Run NESA compliance scan; review Vulnerability Radar; publish developer NPS.
- **Quarterly**: Fleet Upgrade campaign for new framework releases; update Capability Fabric with new skills.
- **Semi-annual**: SOC-2 readiness review; penetration test.
- **On-demand**: New domain agent packs as AD Ports expands to new business units.

---

*Phase 25 — Ecosystem Agents, Scale & Sovereignty (Gate 4 Checkpoint) — AI Portal — v1.0*
