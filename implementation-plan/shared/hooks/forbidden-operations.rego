package adports.hooks.forbidden

import future.keywords.if

# ─── FORBIDDEN OPERATIONS ────────────────────────────────────────────────────
# These operations are UNCONDITIONALLY denied regardless of caller role.
# Source: shared/hooks/forbidden-operations.rego

forbidden_operations := {
    "delete_production_database",
    "force_push_main_branch",
    "force_push_release_branch",
    "destroy_production_infrastructure",
    "modify_keycloak_admin_realm",
    "delete_pipeline_ledger_events",
    "bypass_approval_gate",
    "disable_mfa",
    "remove_network_policy",
    "store_pan_in_database",          # PCI-DSS
    "log_sensitive_data",
    "publish_internal_data_public",
}

forbidden_command_patterns := [
    # Database destruction
    `(?i)DROP\s+DATABASE`,
    `(?i)DROP\s+SCHEMA.*CASCADE`,
    `(?i)TRUNCATE\s+TABLE`,

    # File system destruction
    `rm\s+-[rf]+\s+/`,
    `del\s+/[fs]\s+/q`,

    # Git force push to protected branches
    `git\s+push\s+.*--force.*\b(main|master|release|production)\b`,
    `git\s+push\s+-f\s+.*\b(main|master|release|production)\b`,

    # Infrastructure destruction
    `kubectl\s+delete\s+namespace`,
    `pulumi\s+destroy\s+--yes`,
    `terraform\s+destroy\s+-auto-approve`,
    `az\s+group\s+delete`,

    # Secret exfiltration patterns
    `curl\s+.*\|\s*(bash|sh|python)`,   # Curl-to-bash attacks
    `wget\s+.*\|\s*(bash|sh|python)`,

    # Process hiding
    `>\s*/dev/null\s+2>&1\s+&$`,
]

deny[reason] if {
    input.action.operation in forbidden_operations
    reason := sprintf(
        "Operation '%v' is unconditionally forbidden by AD Ports security policy",
        [input.action.operation]
    )
}

deny[reason] if {
    some pattern in forbidden_command_patterns
    regex.match(pattern, input.action.command)
    reason := sprintf(
        "Command matches forbidden pattern. Potential destructive or malicious operation blocked.",
        []
    )
}

deny[reason] if {
    # Prevent any agent from modifying another project's resources
    input.action.target_project_id != null
    input.action.target_project_id != input.caller.project_id
    not input.caller.roles[_] == "platform_admin"
    reason := sprintf(
        "Cross-project operations are forbidden. Use your own project resources.",
        []
    )
}
