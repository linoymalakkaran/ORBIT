package adports.hooks.budget

import future.keywords.if

# ─── BUDGET LIMITS ────────────────────────────────────────────────────────────
# Enforces per-project LLM cost limits.
# Source: shared/hooks/budget-limits.rego

# Thresholds in USD per project per month
project_budget_thresholds := {
    "default":    {"warn": 30.0,  "block": 50.0},
    "pilot":      {"warn": 50.0,  "block": 100.0},
    "enterprise": {"warn": 200.0, "block": 500.0},
    "internal":   {"warn": 15.0,  "block": 25.0},  # Internal tooling projects
}

# Per-agent max cost per invocation (USD) to catch runaway agents
agent_max_cost_per_invocation := {
    "architecture":   5.00,
    "backend":        3.00,
    "frontend":       3.00,
    "database":       1.00,
    "integration":    1.00,
    "devops":         2.00,
    "qa":             2.00,
    "fleet-upgrade":  8.00,  # Higher — touches many repos
    "ba":             4.00,
    "review":         0.50,
}

default deny_budget := false

deny_budget if {
    threshold := project_budget_thresholds[input.project.tier]
    input.project.current_llm_cost_usd >= threshold.block
}

deny_reason_budget[reason] if {
    deny_budget
    threshold := project_budget_thresholds[input.project.tier]
    reason := sprintf(
        "Project '%v' LLM budget exceeded ($%.2f / $%.2f limit). Architect approval required to continue.",
        [input.project.id, input.project.current_llm_cost_usd, threshold.block]
    )
}

warn_budget[reason] if {
    not deny_budget
    threshold := project_budget_thresholds[input.project.tier]
    input.project.current_llm_cost_usd >= threshold.warn
    pct := (input.project.current_llm_cost_usd / threshold.block) * 100
    reason := sprintf(
        "Project '%v' LLM budget at %.0f%% ($%.2f / $%.2f).",
        [input.project.id, pct, input.project.current_llm_cost_usd, threshold.block]
    )
}

deny_invocation_cost[reason] if {
    max_cost := agent_max_cost_per_invocation[input.action.agent_type]
    input.action.estimated_cost_usd > max_cost
    reason := sprintf(
        "Agent '%v' estimated invocation cost $%.2f exceeds limit $%.2f. Split work into smaller units.",
        [input.action.agent_type, input.action.estimated_cost_usd, max_cost]
    )
}
