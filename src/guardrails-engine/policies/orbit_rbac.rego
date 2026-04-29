# ORBIT Rego Policies — OPA Policy Bundle
# Deploy to OPA sidecar in ai-portal namespace

# ── orbit/rbac/policy.rego ────────────────────────────────────────────────────
package orbit.rbac

default allow = false
default reason = "insufficient role"

# Admins can do anything
allow {
    input.roles[_] == "orbit-admin"
}

# Architects can approve and design
allow {
    input.roles[_] == "orbit-architect"
    input.action in {"architecture_design", "approve_proposal", "deploy_to_prod",
                     "create_repo", "push_code_main"}
}

# Developers can generate and test
allow {
    input.roles[_] == "orbit-developer"
    input.action in {"generate_code", "generate_tests", "generate_docs",
                     "run_integration_tests", "view_proposals"}
}

# QA engineers can run tests
allow {
    input.roles[_] == "orbit-qa"
    input.action in {"run_integration_tests", "run_e2e_tests", "view_reports"}
}

# DevOps engineers can deploy (non-prod)
allow {
    input.roles[_] == "orbit-devops"
    input.action in {"deploy_to_dev", "deploy_to_staging", "view_infrastructure",
                     "run_security_scan"}
}

# Payment project type: only PCI-certified roles
allow {
    input.project_type == "payment"
    input.roles[_] == "orbit-pci-certified"
}

reason = "user has required role" {
    allow
}
