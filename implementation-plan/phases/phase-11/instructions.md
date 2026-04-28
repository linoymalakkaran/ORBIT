# Instructions — Phase 11: LLM Gateway & Cost Management

> Add this file to your IDE's custom instructions when working on LiteLLM configuration, LLM provider integration, or cost controls.

---

## Context

You are working on the **AD Ports LLM Gateway** — a LiteLLM proxy that provides a unified, provider-agnostic interface to all LLM providers used in the Portal. All agent LLM calls MUST go through this gateway. The gateway enforces the `llm-tier-selection.rego` policy, tracks costs per project, and enforces monthly budget limits.

---

## LiteLLM Configuration Structure

```yaml
# litellm-config.yaml
model_list:
  # ── Premium Tier ────────────────────────────────────────────────────────
  - model_name: premium/claude-sonnet-4
    litellm_params:
      model: claude-sonnet-4-20250514
      api_base: https://api.anthropic.com
      api_key: "os.environ/ANTHROPIC_API_KEY"
      max_tokens: 8192
      metadata:
        tier: premium
        cost_per_1k_tokens_input: 0.003
        cost_per_1k_tokens_output: 0.015

  # ── Standard Tier ────────────────────────────────────────────────────────
  - model_name: standard/gpt-4o
    litellm_params:
      model: azure/gpt-4o
      api_base: "os.environ/AZURE_OPENAI_ENDPOINT"
      api_key: "os.environ/AZURE_OPENAI_KEY"
      api_version: "2025-02-01"
      metadata:
        tier: standard
        cost_per_1k_tokens_input: 0.0025
        cost_per_1k_tokens_output: 0.01

  # ── Economy Tier ─────────────────────────────────────────────────────────
  - model_name: economy/deepseek-v3
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: "os.environ/DEEPSEEK_API_KEY"
      metadata:
        tier: economy
        cost_per_1k_tokens_input: 0.00027
        cost_per_1k_tokens_output: 0.0011

  # ── Sovereign Tier (Phase 25) ─────────────────────────────────────────────
  - model_name: sovereign/llama-3.3-70b
    litellm_params:
      model: openai/llama-3.3-70b
      api_base: "os.environ/VLLM_ENDPOINT"
      api_key: "os.environ/VLLM_API_KEY"
      metadata:
        tier: sovereign
        cost_per_1k_tokens_input: 0.0001
        cost_per_1k_tokens_output: 0.0001

litellm_settings:
  callbacks: ["adports_cost_tracker"]    # Custom callback for cost recording
  request_timeout: 60
  drop_params: true

router_settings:
  retry_policy:
    TimeoutErrorRetries: 2
    RateLimitErrorRetries: 3
```

## LiteLLM Call Pattern in Agents

```python
import litellm
from shared.cost_tracker import record_llm_cost

TIER_MODEL_MAP = {
    "premium":   "premium/claude-sonnet-4",
    "standard":  "standard/gpt-4o",
    "economy":   "economy/deepseek-v3",
    "sovereign": "sovereign/llama-3.3-70b",
}

async def call_llm(
    messages: list[dict],
    tier: str,
    project_id: str,
    task_id: str,
) -> str:
    model = TIER_MODEL_MAP[tier]

    response = await litellm.acompletion(
        model=model,
        messages=messages,
        metadata={
            "project_id": project_id,
            "task_id":    task_id,
            "tier":       tier,
        }
    )

    # Always record cost to the Pipeline Ledger
    await record_llm_cost(
        project_id=project_id,
        task_id=task_id,
        model=model,
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        cost_usd=response._hidden_params.get("response_cost", 0),
    )

    return response.choices[0].message.content
```

## Budget Enforcement

```python
# Budget limits per project per month (from budget-limits.rego)
# The gateway enforces these BEFORE making the LLM call

MONTHLY_BUDGET_LIMITS_USD = {
    "pilot":      50.0,
    "standard":  200.0,
    "premium":  1000.0,
}

async def check_budget_before_call(project_id: str, tier: str, estimated_cost: float) -> None:
    current_month_spend = await get_monthly_spend(project_id)
    project_tier = await get_project_tier(project_id)
    limit = MONTHLY_BUDGET_LIMITS_USD[project_tier]

    if current_month_spend + estimated_cost > limit:
        raise BudgetExceededError(
            f"Project {project_id} would exceed monthly budget "
            f"(${current_month_spend:.2f} + ${estimated_cost:.2f} > ${limit:.2f})"
        )
```

## Provider Fallback Chain

```
premium/claude-sonnet-4
    └── on RateLimitError → premium/claude-sonnet-4 (retry after backoff)
    └── on ProviderOutage → standard/gpt-4o (automatic fallback)
        └── on ProviderOutage → economy/deepseek-v3 (secondary fallback)

sovereign/llama-3.3-70b
    └── No fallback — sovereign tier must stay sovereign (classified data)
    └── on vLLM service down → raise SovereignUnavailableError (never route to cloud)
```

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Direct `anthropic.Anthropic()` client in agent code | All calls must go through LiteLLM gateway |
| Hardcoding model names as strings (e.g., `"claude-sonnet-4"`) | Use tier map — model names change |
| Skipping cost recording | Budget tracking is mandatory for every LLM call |
| Routing classified/PII data to a cloud LLM tier | Sovereign tier only — enforced by Hook Engine |
| Disabling timeout for "large" requests | Set `timeout=120` max; break large requests into chunks |

---

*Instructions — Phase 11 — AD Ports AI Portal — Applies to: Platform Squad*
