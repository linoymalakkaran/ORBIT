#!/usr/bin/env bash
# vault-bootstrap.sh — seeds Vault policies and K8s auth roles for all ORBIT services
# Run: VAULT_ADDR=https://vault.ai.adports.ae VAULT_TOKEN=<root_token> bash scripts/vault-bootstrap.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-https://vault.ai.adports.ae}"
NAMESPACE_PORTAL="ai-portal"
NAMESPACE_LITELLM="litellm"

echo "==> Enabling KV v2 secrets engine"
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "Already enabled"

echo "==> Enabling Kubernetes auth method"
vault auth enable kubernetes 2>/dev/null || echo "Already enabled"

echo "==> Configuring Kubernetes auth"
vault write auth/kubernetes/config kubernetes_host="https://kubernetes.default.svc"

# ── Helper functions ──────────────────────────────────────────────────────────
write_policy() {
  local name="$1"
  local rules="$2"
  echo "$rules" | vault policy write "$name" -
  echo "  Policy: $name"
}

write_k8s_role() {
  local name="$1"
  local sa="$2"
  local ns="$3"
  local policy="$4"
  vault write "auth/kubernetes/role/$name" \
    bound_service_account_names="$sa" \
    bound_service_account_namespaces="$ns" \
    policies="$policy" \
    ttl="1h"
  echo "  K8s Role: $name"
}

# ── Policies ─────────────────────────────────────────────────────────────────
SERVICES=(
  portal-api pipeline-ledger capability-fabric orchestrator hook-engine
  project-registry-agent health-monitor-agent pr-review-agent
  ba-agent pm-agent vulnerability-radar-agent fleet-upgrade-agent docs-agent
  mcp-servers
)

for svc in "${SERVICES[@]}"; do
  write_policy "$svc" "path \"secret/data/${svc}/*\" { capabilities = [\"read\"] }
path \"secret/metadata/${svc}/*\" { capabilities = [\"list\", \"read\"] }"
  write_k8s_role "$svc" "$svc" "$NAMESPACE_PORTAL" "$svc"
done

# LiteLLM lives in its own namespace
write_policy "litellm" "path \"secret/data/litellm/*\" { capabilities = [\"read\"] }"
write_k8s_role "litellm" "litellm" "$NAMESPACE_LITELLM" "litellm"

echo ""
echo "==> DONE. Vault bootstrap complete."
echo "==> Next: seed secrets with 'vault kv put secret/<service>/env key=value'"
