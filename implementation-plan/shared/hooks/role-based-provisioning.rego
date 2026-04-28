package adports.hooks

import future.keywords.if
import future.keywords.in

# ─── ROLE-BASED PROVISIONING ────────────────────────────────────────────────
# Defines which roles can invoke which agent types.
# Source: shared/hooks/role-based-provisioning.rego

agent_permissions := {
    "platform_admin":    {"*"},
    "architect":         {"architecture", "backend", "frontend", "database", "integration", "devops", "qa", "review", "fleet-upgrade"},
    "senior_developer":  {"backend", "frontend", "database", "integration", "qa", "review"},
    "developer":         {"backend", "frontend", "qa"},
    "pm":                {"architecture", "ba"},
    "ba":                {"ba"},
    "viewer":            set()
}

production_restricted_roles := {"platform_admin", "architect"}

default allow_provisioning := false

allow_provisioning if {
    caller_roles := {r | r = input.caller.roles[_]}
    allowed_agents := {a | agent_permissions[r][a]; r = caller_roles[_]}
    input.action.agent_type in allowed_agents
}

allow_provisioning if {
    # Wildcard permission (platform_admin)
    caller_roles := {r | r = input.caller.roles[_]}
    some r in caller_roles
    "*" in agent_permissions[r]
}

deny_provisioning[reason] if {
    not allow_provisioning
    reason := sprintf(
        "Role '%v' is not permitted to invoke agent type '%v'",
        [concat(",", input.caller.roles), input.action.agent_type]
    )
}

deny_provisioning[reason] if {
    input.action.target_environment == "production"
    not input.caller.roles[_] in production_restricted_roles
    reason := "Production operations require architect or platform_admin role"
}

deny_provisioning[reason] if {
    not project_member(input.caller.user_id, input.action.project_id)
    reason := sprintf(
        "User '%v' is not a member of project '%v'",
        [input.caller.user_id, input.action.project_id]
    )
}

project_member(user_id, project_id) if {
    data.projects[project_id].members[_].user_id == user_id
}
