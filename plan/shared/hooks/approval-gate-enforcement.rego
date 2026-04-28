# AD Ports — Approval Gate Enforcement Policy
package adports.hooks.approval_gates

import future.keywords.if
import future.keywords.in

# ─── Input contract ───────────────────────────────────────────────────────────
# input.action.type       string   — The action type being requested
# input.project.id        string   — Portal project ID
# input.project.stage     string   — Current project workflow stage
# input.approvals         array    — List of recorded approvals for this project
#   each approval: { id, stage, approver_id, approver_roles, timestamp, signature_valid }
# input.caller.user_id    string   — User attempting the action
# input.caller.roles      array    — Keycloak roles for calling user
# ─────────────────────────────────────────────────────────────────────────────

default allow := false
default approval_gate_passed := false

# Allow if gate passes and no denials
allow if {
    approval_gate_passed
    count(deny) == 0
}

# Gate passes when required approvals for this action are all present
approval_gate_passed if {
    required := required_approvals_for_action[input.action.type]
    every gate in required {
        gate_satisfied(gate)
    }
}

# Action does not require any approval gate
approval_gate_passed if {
    not required_approvals_for_action[input.action.type]
}

# ─── Gate satisfaction check ──────────────────────────────────────────────────

# A gate is satisfied if there is a valid approval from the required role at the required stage
gate_satisfied(gate) if {
    some approval in input.approvals
    approval.stage       == gate.required_stage
    approval.signature_valid == true
    gate.required_role in approval.approver_roles
    not approval_expired(approval, gate.validity_hours)
}

# Approval expires after gate.validity_hours hours
approval_expired(approval, validity_hours) if {
    now_unix  := time.now_ns() / 1000000000
    issued_at := time.parse_rfc3339_ns(approval.timestamp) / 1000000000
    age_hours := (now_unix - issued_at) / 3600
    age_hours > validity_hours
}

# ─── Required approvals per action ────────────────────────────────────────────
#
# Structure: action_type → array of gate objects
# Gate object: {
#   required_stage:   stage that must have been approved
#   required_role:    Keycloak role the approver must hold
#   validity_hours:   how long the approval is valid (0 = forever)
# }

required_approvals_for_action := {
    # Starting the backend agent requires an approved architecture
    "backend_agent.start": [
        {
            "required_stage":  "architecture_review",
            "required_role":   "architect",
            "validity_hours":  168    # 1 week — architecture does not expire quickly
        }
    ],

    # Starting the frontend agent requires an approved architecture
    "frontend_agent.start": [
        {
            "required_stage":  "architecture_review",
            "required_role":   "architect",
            "validity_hours":  168
        }
    ],

    # Starting the devops agent requires architecture + code review sign-off
    "devops_agent.start": [
        {
            "required_stage":  "architecture_review",
            "required_role":   "architect",
            "validity_hours":  168
        },
        {
            "required_stage":  "code_review",
            "required_role":   "senior_developer",
            "validity_hours":  48    # Code review expires after 48h
        }
    ],

    # Fleet upgrade campaign requires two-person approval (architect + devops lead)
    "fleet_upgrade.start": [
        {
            "required_stage":  "fleet_campaign_review",
            "required_role":   "architect",
            "validity_hours":  24
        },
        {
            "required_stage":  "fleet_campaign_review",
            "required_role":   "devops_lead",
            "validity_hours":  24
        }
    ],

    # Emergency override requires platform admin sign-off
    "policy.emergency_override": [
        {
            "required_stage":  "emergency_override_request",
            "required_role":   "platform_admin",
            "validity_hours":  1    # Very short validity — emergencies are time-bound
        }
    ],

    # Production deployment requires two-person rule
    "infra_agent.deploy_production": [
        {
            "required_stage":  "architecture_review",
            "required_role":   "architect",
            "validity_hours":  72
        },
        {
            "required_stage":  "production_deploy_approval",
            "required_role":   "delivery_lead",
            "validity_hours":  4    # Production deploy approval expires in 4 hours
        }
    ],

    # Ledger compliance export requires auditor approval
    "ledger.export_compliance_package": [
        {
            "required_stage":  "compliance_export_request",
            "required_role":   "auditor",
            "validity_hours":  8
        }
    ],

    # CVSS ≥ 9 CVE remediation can bypass normal gates but needs security lead sign-off
    "vulnerability.emergency_patch": [
        {
            "required_stage":  "security_emergency_approval",
            "required_role":   "security_lead",
            "validity_hours":  2
        }
    ],
}

# ─── Two-person rule enforcement ──────────────────────────────────────────────
# For fleet upgrades and production deploys, the two approvers MUST be different people.

deny contains reason if {
    input.action.type in two_person_required_actions
    not two_distinct_approvers
    reason := sprintf(
        "Action %v requires two distinct approvers. Same person cannot approve twice.",
        [input.action.type]
    )
}

two_person_required_actions := {
    "fleet_upgrade.start",
    "infra_agent.deploy_production",
}

two_distinct_approvers if {
    approvers := { approval.approver_id | some approval in input.approvals }
    count(approvers) >= 2
}

# ─── Self-approval ban ─────────────────────────────────────────────────────────
# The person requesting an action cannot be the approver.

deny contains reason if {
    some approval in input.approvals
    approval.approver_id == input.caller.user_id
    reason := sprintf(
        "Self-approval is not permitted. User %v cannot approve their own request.",
        [input.caller.user_id]
    )
}

# ─── Expired approval block ────────────────────────────────────────────────────

deny contains reason if {
    required := required_approvals_for_action[input.action.type]
    some gate in required
    some approval in input.approvals
    approval.stage == gate.required_stage
    approval_expired(approval, gate.validity_hours)
    reason := sprintf(
        "Approval for stage %v has expired. Re-approval required.",
        [gate.required_stage]
    )
}

# ─── Invalid signature block ───────────────────────────────────────────────────
# Approvals with invalid digital signatures are treated as non-existent.

deny contains reason if {
    some approval in input.approvals
    not approval.signature_valid
    reason := sprintf(
        "Approval %v has an invalid digital signature. Approval is void.",
        [approval.id]
    )
}
