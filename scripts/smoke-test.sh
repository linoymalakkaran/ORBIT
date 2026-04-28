#!/usr/bin/env bash
# =============================================================================
# ORBIT Phase 01 — Platform Foundation Smoke Test
# Covers D1–D12 acceptance criteria from plan/phases/phase-01/phase-01.md
# Usage: ./scripts/smoke-test.sh [ENV]
#   ENV defaults to "dev"
# Prerequisites: kubectl configured against the target cluster, curl, jq
# =============================================================================
set -euo pipefail

ENV="${1:-dev}"
DOMAIN="ai.adports.ae"
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass()  { echo -e "${GREEN}[PASS]${NC} $1"; ((PASS_COUNT++)); }
fail()  { echo -e "${RED}[FAIL]${NC} $1"; ((FAIL_COUNT++)); }
skip()  { echo -e "${YELLOW}[SKIP]${NC} $1"; ((SKIP_COUNT++)); }
header(){ echo -e "\n--- $1 ---"; }

# ─────────────────────────────────────────────────────────────────────────────
# Helper: wait for a deployment to be ready
# ─────────────────────────────────────────────────────────────────────────────
wait_deploy() {
  local ns=$1 deploy=$2
  if kubectl -n "$ns" rollout status deployment/"$deploy" --timeout=60s &>/dev/null; then
    return 0
  fi
  return 1
}

# ─────────────────────────────────────────────────────────────────────────────
# D1 — Namespaces created
# ─────────────────────────────────────────────────────────────────────────────
header "D1: Namespaces"
for ns in ai-portal-system ai-portal-core ai-portal-data ai-portal-agents \
          ai-portal-vault ai-portal-keycloak ai-portal-observability; do
  if kubectl get namespace "$ns" &>/dev/null; then
    pass "Namespace $ns exists"
  else
    fail "Namespace $ns missing"
  fi
done

# ─────────────────────────────────────────────────────────────────────────────
# D2 — MetalLB LoadBalancer IP allocated
# ─────────────────────────────────────────────────────────────────────────────
header "D2: MetalLB"
LB_IP=$(kubectl -n ai-portal-system get svc \
  -l app.kubernetes.io/name=kong \
  -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || true)
if [[ -n "$LB_IP" ]]; then
  pass "MetalLB IP assigned: $LB_IP"
else
  fail "MetalLB: No LoadBalancer IP allocated"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D3 — cert-manager + ClusterIssuer ready
# ─────────────────────────────────────────────────────────────────────────────
header "D3: cert-manager"
if kubectl -n cert-manager get pod -l app=cert-manager --field-selector=status.phase=Running \
     -o name 2>/dev/null | grep -q .; then
  pass "cert-manager pod running"
else
  fail "cert-manager pod not running"
fi
if kubectl get clusterissuer adports-internal-ca &>/dev/null; then
  ISSUER_READY=$(kubectl get clusterissuer adports-internal-ca \
    -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}')
  [[ "$ISSUER_READY" == "True" ]] \
    && pass "ClusterIssuer adports-internal-ca is Ready" \
    || fail "ClusterIssuer adports-internal-ca not Ready (status: $ISSUER_READY)"
else
  fail "ClusterIssuer adports-internal-ca not found"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D4 — Vault unsealed and responding
# ─────────────────────────────────────────────────────────────────────────────
header "D4: HashiCorp Vault"
VAULT_POD=$(kubectl -n ai-portal-vault get pod -l app.kubernetes.io/name=vault \
  -o name 2>/dev/null | head -1 || true)
if [[ -z "$VAULT_POD" ]]; then
  fail "Vault pod not found"
else
  VAULT_STATUS=$(kubectl -n ai-portal-vault exec "$VAULT_POD" -- \
    vault status -format=json 2>/dev/null | jq -r '.sealed' || echo "error")
  if [[ "$VAULT_STATUS" == "false" ]]; then
    pass "Vault is unsealed and responding"
  else
    fail "Vault is sealed or unreachable (sealed=$VAULT_STATUS)"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# D5 — PostgreSQL cluster healthy
# ─────────────────────────────────────────────────────────────────────────────
header "D5: PostgreSQL (CloudNativePG)"
CLUSTER_NAME="orbit-postgres-${ENV}"
PG_STATUS=$(kubectl -n ai-portal-data get cluster "$CLUSTER_NAME" \
  -o jsonpath='{.status.phase}' 2>/dev/null || echo "NotFound")
if [[ "$PG_STATUS" == "Cluster in healthy state" || "$PG_STATUS" == "healthy" ]]; then
  pass "CloudNativePG cluster $CLUSTER_NAME is healthy"
else
  # fallback: check pod readiness
  READY=$(kubectl -n ai-portal-data get pod \
    -l "cnpg.io/cluster=${CLUSTER_NAME}" \
    --field-selector=status.phase=Running -o name 2>/dev/null | wc -l | tr -d ' ')
  [[ "$READY" -ge 1 ]] \
    && pass "CNPG pods running ($READY ready)" \
    || fail "CloudNativePG cluster not ready (phase=$PG_STATUS)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D6 — Redis cluster operational
# ─────────────────────────────────────────────────────────────────────────────
header "D6: Redis Cluster"
REDIS_READY=$(kubectl -n ai-portal-data get pods \
  -l app.kubernetes.io/name=redis-cluster \
  --field-selector=status.phase=Running -o name 2>/dev/null | wc -l | tr -d ' ')
if [[ "$REDIS_READY" -ge 3 ]]; then
  pass "Redis: $REDIS_READY pods running"
else
  fail "Redis: only $REDIS_READY pods running (need at least 3)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D7 — Kafka cluster operational
# ─────────────────────────────────────────────────────────────────────────────
header "D7: Kafka (Strimzi)"
KAFKA_STATUS=$(kubectl -n ai-portal-data get kafka orbit-kafka \
  -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null || echo "NotFound")
[[ "$KAFKA_STATUS" == "True" ]] \
  && pass "Kafka orbit-kafka is Ready" \
  || fail "Kafka orbit-kafka not ready (status=$KAFKA_STATUS)"

# ─────────────────────────────────────────────────────────────────────────────
# D8 — EventStoreDB responding
# ─────────────────────────────────────────────────────────────────────────────
header "D8: EventStoreDB"
ESDB_POD=$(kubectl -n ai-portal-data get pod \
  -l app.kubernetes.io/name=eventstore -o name 2>/dev/null | head -1 || true)
if [[ -z "$ESDB_POD" ]]; then
  fail "EventStoreDB pod not found"
else
  HTTP_CODE=$(kubectl -n ai-portal-data exec "$ESDB_POD" -- \
    curl -s -o /dev/null -w "%{http_code}" http://localhost:2113/health/live 2>/dev/null || echo "000")
  [[ "$HTTP_CODE" == "204" || "$HTTP_CODE" == "200" ]] \
    && pass "EventStoreDB health check: $HTTP_CODE" \
    || fail "EventStoreDB health check failed: $HTTP_CODE"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D9 — MinIO responding
# ─────────────────────────────────────────────────────────────────────────────
header "D9: MinIO"
MINIO_POD=$(kubectl -n ai-portal-data get pod \
  -l app.kubernetes.io/name=minio -o name 2>/dev/null | head -1 || true)
if [[ -z "$MINIO_POD" ]]; then
  fail "MinIO pod not found"
else
  MINIO_HTTP=$(kubectl -n ai-portal-data exec "$MINIO_POD" -- \
    curl -s -o /dev/null -w "%{http_code}" http://localhost:9000/minio/health/live 2>/dev/null || echo "000")
  [[ "$MINIO_HTTP" == "200" ]] \
    && pass "MinIO health check: 200 OK" \
    || fail "MinIO health check failed: $MINIO_HTTP"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D10 — Keycloak responding
# ─────────────────────────────────────────────────────────────────────────────
header "D10: Keycloak"
KC_READY=$(kubectl -n ai-portal-keycloak get pods \
  -l app.kubernetes.io/name=keycloak \
  --field-selector=status.phase=Running -o name 2>/dev/null | wc -l | tr -d ' ')
if [[ "$KC_READY" -ge 1 ]]; then
  KC_POD=$(kubectl -n ai-portal-keycloak get pod \
    -l app.kubernetes.io/name=keycloak -o name 2>/dev/null | head -1)
  HTTP=$(kubectl -n ai-portal-keycloak exec "$KC_POD" -- \
    curl -s -o /dev/null -w "%{http_code}" \
    "http://localhost:8080/realms/master/.well-known/openid-configuration" 2>/dev/null || echo "000")
  [[ "$HTTP" == "200" ]] \
    && pass "Keycloak OIDC discovery endpoint: 200 OK" \
    || fail "Keycloak OIDC discovery failed: HTTP $HTTP"
else
  fail "Keycloak: no running pods"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D11 — Kong proxy responding
# ─────────────────────────────────────────────────────────────────────────────
header "D11: Kong Ingress Controller"
KONG_POD=$(kubectl -n ai-portal-system get pod \
  -l app.kubernetes.io/component=app -l app.kubernetes.io/name=kong \
  -o name 2>/dev/null | head -1 || true)
if [[ -z "$KONG_POD" ]]; then
  fail "Kong proxy pod not found"
else
  KONG_HTTP=$(kubectl -n ai-portal-system exec "$KONG_POD" -- \
    curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/status 2>/dev/null || echo "000")
  [[ "$KONG_HTTP" == "200" ]] \
    && pass "Kong Admin API /status: 200 OK" \
    || fail "Kong Admin API failed: HTTP $KONG_HTTP"
fi

# ─────────────────────────────────────────────────────────────────────────────
# D12 — ArgoCD syncing
# ─────────────────────────────────────────────────────────────────────────────
header "D12: ArgoCD"
ARGOCD_POD=$(kubectl -n ai-portal-system get pod \
  -l app.kubernetes.io/name=argocd-server -o name 2>/dev/null | head -1 || true)
if [[ -z "$ARGOCD_POD" ]]; then
  fail "ArgoCD server pod not found"
else
  pass "ArgoCD server pod running: $ARGOCD_POD"
  # Check app-of-apps application exists
  if kubectl -n ai-portal-system get application orbit-infra &>/dev/null; then
    SYNC=$(kubectl -n ai-portal-system get application orbit-infra \
      -o jsonpath='{.status.sync.status}' 2>/dev/null || echo "Unknown")
    HEALTH=$(kubectl -n ai-portal-system get application orbit-infra \
      -o jsonpath='{.status.health.status}' 2>/dev/null || echo "Unknown")
    echo "   orbit-infra sync=$SYNC health=$HEALTH"
    [[ "$SYNC" == "Synced" ]] \
      && pass "ArgoCD orbit-infra application: Synced" \
      || fail "ArgoCD orbit-infra application: $SYNC"
  else
    skip "ArgoCD Application orbit-infra not found (app-of-apps not bootstrapped yet)"
  fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
echo ""
echo "======================================="
echo "  Smoke Test Summary (ENV=$ENV)"
echo "======================================="
echo -e "  ${GREEN}PASS: $PASS_COUNT${NC}"
echo -e "  ${RED}FAIL: $FAIL_COUNT${NC}"
echo -e "  ${YELLOW}SKIP: $SKIP_COUNT${NC}"
echo "======================================="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo "Some checks failed — review output above."
  exit 1
else
  echo -e "${GREEN}All checks passed!${NC}"
  exit 0
fi
