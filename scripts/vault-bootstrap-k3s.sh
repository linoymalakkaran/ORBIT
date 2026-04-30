#!/usr/bin/env bash
# vault-bootstrap-k3s.sh — Seeds Vault for k3s deployment
# Same as vault-bootstrap.sh but Vault address points to NodePort
#
# Usage:
#   VAULT_ADDR=http://SERVER_IP:30082 VAULT_TOKEN=<root_token> bash scripts/vault-bootstrap-k3s.sh
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:30082}"
VAULT_TOKEN="${VAULT_TOKEN:?Set VAULT_TOKEN=<root_token>}"
NAMESPACE_PORTAL="ai-portal"
NAMESPACE_LITELLM="litellm"

export VAULT_ADDR VAULT_TOKEN

echo "==> Vault address: $VAULT_ADDR"

echo "==> Enabling KV v2 secrets engine"
vault secrets enable -path=secret kv-v2 2>/dev/null || echo "Already enabled"

echo "==> Enabling Kubernetes auth method"
vault auth enable kubernetes 2>/dev/null || echo "Already enabled"

echo "==> Configuring Kubernetes auth (k3s API server)"
# k3s uses the same kubernetes.default.svc endpoint
vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc"

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
  architecture-agent backend-specialist-agent frontend-specialist-agent
  database-agent devops-agent qa-agent integration-test-agent
  guardrails-engine project-registry service-health-monitor ticket-agent
)

for svc in "${SERVICES[@]}"; do
  write_policy "$svc" "path \"secret/data/${svc}/*\" { capabilities = [\"read\"] }
path \"secret/metadata/${svc}/*\" { capabilities = [\"list\", \"read\"] }"
  write_k8s_role "$svc" "$svc" "$NAMESPACE_PORTAL" "$svc"
done

write_policy "litellm" "path \"secret/data/litellm/*\" { capabilities = [\"read\"] }"
write_k8s_role "litellm" "litellm" "$NAMESPACE_LITELLM" "litellm"

write_policy "llama-inference" "path \"secret/data/llama-inference/*\" { capabilities = [\"read\"] }"
write_k8s_role "llama-inference" "llama-inference" "sovereign-ai" "llama-inference"

# ── Seed example secrets (change values before using) ────────────────────────
echo ""
echo "==> Seeding example secrets (update values for your environment)"

vault kv put secret/portal-api/openfga \
  postgres_uri="postgresql://orbit_app:orbit-pg-password@orbit-postgres-rw.ai-portal-data.svc.cluster.local:5432/ai_portal?sslmode=disable"

vault kv put secret/litellm/env \
  master_key="sk-orbit-master-key" \
  db_url="postgresql://orbit_app:orbit-pg-password@orbit-postgres-rw.ai-portal-data.svc.cluster.local:5432/ai_portal" \
  azure_openai_endpoint="" \
  azure_openai_key=""

vault kv put secret/orchestrator/litellm \
  api_key="sk-orbit-master-key"

echo ""
echo "==> DONE. Vault bootstrap complete."
echo ""
echo "==> Vault UI: ${VAULT_ADDR}/ui"
echo "==> Update secrets: vault kv put secret/<service>/env key=value"
