# Instructions — Phase 25: Scale, Sovereignty & Domain Packs

> Add this file to your IDE's custom instructions when working on sovereign LLM deployment, NESA compliance, or domain intelligence packs.

---

## Context

You are working on **Scale, Sovereignty & Domain Packs** — the final phase of the AD Ports AI Portal. This phase deploys a sovereign self-hosted LLM on AKS GPU nodes (vLLM + Llama 3.3), ensures NESA (National Electronic Security Authority, UAE) regulatory compliance, and packages domain-specific knowledge packs (DGD, LCS, CRUISE) that specialise the AI agents for AD Ports' core business verticals.

---

## Sovereign LLM: vLLM on AKS GPU

### AKS Node Pool for GPU

```yaml
# Pulumi IaC — GPU node pool
const gpuNodePool = new azure.containerservice.ManagedClusterAgentPoolProfile("gpu-pool", {
    name:      "gpupool",
    vmSize:    "Standard_NC24ads_A100_v4",  # A100 80GB VRAM
    count:     2,
    mode:      "User",
    nodeTaints: ["sku=gpu:NoSchedule"],
    nodeLabels: {
        "adports.ae/pool-type":    "gpu",
        "adports.ae/sovereignty":  "true",
    },
});
```

### vLLM Deployment

```yaml
# helm/vllm/values.yaml
model:
  name: meta-llama/Llama-3.3-70B-Instruct
  hfTokenSecret: vault/ai-portal/shared/huggingface-token
  quantization: awq            # 4-bit quantization for A100 80GB
  maxModelLen: 32768
  tensorParallelSize: 2        # 2 GPUs per replica

replicaCount: 2                # HA — minimum 2 replicas
resources:
  limits:
    nvidia.com/gpu: "1"        # 1 GPU per pod (tensor parallel across GPUs in pod)
    memory: "160Gi"

tolerations:
  - key: sku
    operator: Equal
    value: gpu
    effect: NoSchedule

# vLLM serves OpenAI-compatible API — LiteLLM routes to it
service:
  port: 8000
  type: ClusterIP              # Internal only — no external exposure
```

### LiteLLM Sovereign Route

```yaml
# litellm-config.yaml addition
- model_name: sovereign/llama-3.3-70b
  litellm_params:
    model: openai/meta-llama/Llama-3.3-70B-Instruct
    api_base: "http://vllm-service.ai-portal-sovereign:8000/v1"
    api_key: "os.environ/VLLM_SERVICE_TOKEN"
    metadata:
      tier: sovereign
      data_residency: UAE
      can_process_classified: true
```

## NESA Compliance Requirements

The following NESA controls apply to the AI Portal (UAE National Cybersecurity Strategy):

| NESA Control | Requirement | Implementation |
|-------------|-------------|---------------|
| SM-3 | Data residency in UAE for sensitive data | Sovereign tier routes classified data to vLLM in AKS (UAE region) |
| IM-2 | Identity management with UAE digital identity | Keycloak federated to UAE Pass (Phase 25 extension) |
| TP-1 | Third-party risk assessment for AI providers | LLM provider assessments in Pipeline Ledger |
| SM-6 | Encryption at rest and in transit | Azure Disk Encryption + TLS 1.3 everywhere |
| BC-2 | Business continuity for critical systems | Sovereign LLM has 2-replica HA deployment |
| AM-3 | Asset management and classification | All data tagged with sensitivity level in OpenFGA |

### Data Classification Policy

```python
class DataClassification(str, Enum):
    PUBLIC         = "PUBLIC"          # Can use any LLM tier
    INTERNAL       = "INTERNAL"        # Standard or Economy tier (no external PII)
    CONFIDENTIAL   = "CONFIDENTIAL"    # Standard tier only (Azure UAE region)
    CLASSIFIED     = "CLASSIFIED"      # Sovereign tier ONLY (vLLM on AKS UAE)
    SECRET         = "SECRET"          # Not processed by AI Portal (human only)

# Hook Engine enforces: CLASSIFIED → sovereign tier only
# This is validated by llm-tier-selection.rego
```

## Domain Intelligence Packs

Domain packs are Fabric bundles that contain domain-specific knowledge:

```yaml
# domain-pack structure
domain-pack-dgd/
├── manifest.yaml             ← Pack metadata and skill list
├── skills/
│   ├── dgd-form-rules.md     ← DGD form validation business rules
│   ├── imdg-code-lookup.md   ← IMDG dangerous goods classification
│   └── un-number-extractor.md ← UN Number extraction from cargo descriptions
├── specs/
│   ├── dgd-declaration.schema.json    ← DGD form data schema
│   └── imdg-class.schema.json         ← IMDG hazard class schema
├── prompts/
│   ├── dgd-risk-assessment.md         ← Prompt for DGD risk scoring
│   └── dgd-compliance-checker.md      ← Prompt for ISPS/IMDG compliance check
├── glossary.yaml             ← Domain terms (cargo types, port codes, hazmat terms)
└── golden-cases/             ← 20+ domain-specific test cases
```

### Pack Manifest

```yaml
# domain-pack-dgd/manifest.yaml
packId:         dgd-domain-pack
displayName:    Dangerous Goods Declarations
version:        1.2.0
domain:         ports-operations
status:         active
maintainer:     ports-ops-squad@adports.ae
activatedFor:   [dgd-pilot-001, dgd-prod-001]   # Projects with this pack active

skills:
  - id: dgd-form-rules
    file: skills/dgd-form-rules.md
  - id: imdg-code-lookup
    file: skills/imdg-code-lookup.md

# Pack activation: POST /api/fabric/domain-packs/{packId}/activate
# with: { "projectId": "...", "activatedBy": "..." }
# Records to Pipeline Ledger
```

## Sovereign LLM Monitoring

```yaml
# Grafana dashboard additions for sovereign LLM
panels:
  - title: "Sovereign LLM Request Rate"
    metric: vllm_request_success_total
  - title: "Token Throughput (tokens/sec)"
    metric: vllm_tokens_per_second
  - title: "GPU Utilization"
    metric: dcgm_fi_dev_gpu_util
  - title: "Queue Wait Time P99"
    metric: vllm_request_queue_time_seconds{quantile="0.99"}
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Exposing vLLM API outside the cluster | Sovereign LLM is internal-only — no external ingress |
| Using sovereign tier for PUBLIC data | Waste of GPU resources — use economy tier |
| Deploying domain pack without test cases | Packs must have ≥ 10 golden test cases before activation |
| Storing CLASSIFIED data in EventStoreDB | EventStoreDB streams are cloud-backed — use separate on-premises store for SECRET/CLASSIFIED |

---

*Instructions — Phase 25 — AD Ports AI Portal — Applies to: Platform Squad + Governance Squad*
