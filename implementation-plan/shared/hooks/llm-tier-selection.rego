# AD Ports — LLM Tier Selection Policy
package adports.hooks.llm_tier_selection

import future.keywords.if
import future.keywords.in

# ─── Input contract ───────────────────────────────────────────────────────────
# input.action.type           string   — The agent action type
# input.task.description      string   — Human-readable task description
# input.task.sensitivity      string   — "HIGH"|"MEDIUM"|"LOW"
# input.task.contains_pii     bool     — Whether task data contains PII
# input.task.is_classified    bool     — Whether data is classified/restricted
# input.project.tier          string   — "pilot"|"enterprise"|"default"
# input.project.domain        string   — "DGD"|"MPay"|"JUL"|"PCS"|"CRM"|"ERP"|"NEW"
# input.caller.roles          array    — Keycloak roles for calling user
# ─────────────────────────────────────────────────────────────────────────────

# Tier selection result
# Returns one of: "premium", "standard", "economy", "sovereign"

default selected_tier := "standard"

# ─── Tier assignment rules (evaluated in priority order) ──────────────────────

# Rule 1: Classified / Sovereign-required data → always sovereign
selected_tier := "sovereign" if {
    input.task.is_classified == true
}

# Rule 2: PII-containing data for restricted domains → sovereign
selected_tier := "sovereign" if {
    input.task.contains_pii == true
    input.project.domain in sovereign_preferred_domains
}

# Rule 3: HIGH sensitivity + CRITICAL domain → sovereign
selected_tier := "sovereign" if {
    input.task.sensitivity == "HIGH"
    input.project.domain in critical_domains
}

# Rule 4: Architecture and review tasks → premium (Claude Sonnet 4.x)
selected_tier := "premium" if {
    not requires_sovereign(input)
    input.action.type in premium_tier_actions
}

# Rule 5: HIGH sensitivity (non-classified) → premium
selected_tier := "premium" if {
    not requires_sovereign(input)
    input.task.sensitivity == "HIGH"
    not input.project.domain in critical_domains
}

# Rule 6: Standard actions → standard (GPT-4o)
selected_tier := "standard" if {
    not requires_sovereign(input)
    not input.action.type in premium_tier_actions
    not input.action.type in economy_tier_actions
}

# Rule 7: Bulk / cheap / repetitive generation → economy (DeepSeek-V3)
selected_tier := "economy" if {
    not requires_sovereign(input)
    input.action.type in economy_tier_actions
}

# ─── Helper rules ─────────────────────────────────────────────────────────────

requires_sovereign(inp) if {
    inp.task.is_classified == true
}

requires_sovereign(inp) if {
    inp.task.contains_pii == true
    inp.project.domain in sovereign_preferred_domains
}

requires_sovereign(inp) if {
    inp.task.sensitivity == "HIGH"
    inp.project.domain in critical_domains
}

# ─── Domain classification ────────────────────────────────────────────────────

# These domains may never send data to cloud LLMs when PII or classified data is involved
sovereign_preferred_domains := {
    "MPay",     # Payment card data (PCI-DSS scope)
    "DGD",      # Customs declarations (government-sensitive)
    "PCS",      # Port operations (ISPS security)
    "JUL",      # Logistics manifests (cargo security)
}

# These domains have CRITICAL asset criticality
critical_domains := {
    "MPay",
    "DGD",
    "PCS",
}

# ─── Action tier assignments ──────────────────────────────────────────────────

# Actions requiring highest reasoning quality → Claude Sonnet 4.x
premium_tier_actions := {
    "architecture_agent.generate_proposal",     # Critical reasoning about system design
    "architecture_agent.review_proposal",       # Quality judgment
    "pr_review_agent.review_pr",                # Code quality judgment
    "orchestrator.decompose_work_packages",     # Planning quality is critical
    "orchestrator.extract_intent",              # High-stakes first step
    "qa_agent.generate_acceptance_criteria",   # Precision required
    "vulnerability_radar.assess_cve",          # Security judgment
}

# Actions that are cheap and high-volume → DeepSeek-V3
economy_tier_actions := {
    "backend_agent.generate_unit_tests",        # High-volume, pattern-based
    "backend_agent.generate_comments",          # Trivial
    "frontend_agent.generate_html_template",    # Template-based
    "brd_parser.extract_sections",              # Structural parsing
    "story_generator.generate_sprint_plan",     # Formulaic
    "health_monitor.generate_runbook_summary",  # Structured output
    "integration_agent.generate_postman_collection", # Template-based
    "devops_agent.generate_helm_values",        # Template-based
    "fleet_upgrade.generate_upgrade_pr_body",   # Template-based
}

# ─── Cost cap per tier ────────────────────────────────────────────────────────
# Maximum cost in cents for a SINGLE LLM call at each tier.
# Exceeding this triggers a cost warning alert.

tier_cost_cap_cents := {
    "premium":   500,     # $5.00 per call max
    "standard":  300,     # $3.00 per call max
    "economy":    50,     # $0.50 per call max
    "sovereign":   0,     # Self-hosted — marginal cost only (GPU time)
}

# ─── Compliance metadata ─────────────────────────────────────────────────────

# Data residency check — sovereign tier required for UAE government data
deny_cloud_llm if {
    input.task.is_classified == true
    selected_tier != "sovereign"
}

compliance_note := note if {
    selected_tier == "sovereign"
    note := "Task routed to sovereign (self-hosted Llama 3.3 70B on AKS GPU). Data does not leave AD Ports infrastructure."
}

compliance_note := note if {
    selected_tier != "sovereign"
    note := sprintf("Task routed to %v tier (cloud LLM). Ensure no classified or PCI-DSS scoped data in prompt.", [selected_tier])
}
