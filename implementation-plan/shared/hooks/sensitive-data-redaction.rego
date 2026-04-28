package adports.hooks.redaction

import future.keywords.if

# ─── SENSITIVE DATA REDACTION POLICY ─────────────────────────────────────────
# Defines what must be redacted from prompts before they reach the LLM gateway.
# The actual regex-based redaction is implemented in Python (Hook Engine).
# This Rego policy validates that the scrubber ran and no bypass was attempted.
# Source: shared/hooks/sensitive-data-redaction.rego

# Data classification levels
classified_data_indicators := [
    "CLASSIFIED",
    "SECRET",
    "TOP SECRET",
    "UAE GOVERNMENT CONFIDENTIAL",
    "ADPORTS CONFIDENTIAL",
]

# Required: scrubber must run on all prompts before reaching LLM
deny[reason] if {
    not input.action.scrubber_ran
    reason := "Prompt scrubber did not run. All LLM prompts must pass through the sensitive data scrubber."
}

# Deny if any classified markers found in the already-scrubbed prompt
deny[reason] if {
    some marker in classified_data_indicators
    contains(input.action.prompt, marker)
    reason := sprintf(
        "Classified data marker '%v' found in prompt. Classified data must not be sent to any LLM.",
        [marker]
    )
}

# Deny if prompt contains patterns indicating raw credentials that scrubber missed
deny[reason] if {
    regex.match(`(?i)password\s*[:=]\s*[^\s\[]{4,}`, input.action.prompt)
    not contains(input.action.prompt, "[REDACTED:")
    reason := "Potential unredacted password found in prompt. Scrubber may have failed."
}

# Force sovereign tier if data is classified
require_sovereign_tier if {
    input.project.data_classification == "CLASSIFIED"
}

require_sovereign_tier if {
    input.action.sensitivity == "HIGH"
    input.project.data_classification in {"INTERNAL", "CLASSIFIED"}
}

# LLM tier selection
recommended_tier := "sovereign"  if { require_sovereign_tier }
recommended_tier := "premium"    if { not require_sovereign_tier; input.action.sensitivity == "HIGH" }
recommended_tier := "standard"   if { not require_sovereign_tier; input.action.sensitivity == "STANDARD" }
recommended_tier := "economy"    if { not require_sovereign_tier; input.action.sensitivity == "ECONOMY" }
