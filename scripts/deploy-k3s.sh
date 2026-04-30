#!/usr/bin/env bash
# =============================================================================
# deploy-k3s.sh — Full ORBIT platform deploy to remote k3s from local machine
#
# Prerequisites (on your local Windows/Linux/Mac machine):
#   - kubectl   : https://kubernetes.io/docs/tasks/tools/
#   - helm      : https://helm.sh/docs/intro/install/
#   - ssh/sshpass (for kubeconfig fetch)
#
# Usage:
#   SERVER_IP=1.2.3.4 SERVER_PASS=mypass ./scripts/deploy-k3s.sh
#   SERVER_IP=1.2.3.4 SSH_KEY=~/.ssh/id_rsa ./scripts/deploy-k3s.sh
#
# To deploy individual components only:
#   COMPONENTS="vault kafka" SERVER_IP=1.2.3.4 ./scripts/deploy-k3s.sh
#
# =============================================================================
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────────────
SERVER_IP="${SERVER_IP:?Set SERVER_IP=your.server.ip}"
SERVER_USER="${SERVER_USER:-root}"
ORBIT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KUBECONFIG_FILE="${HOME}/.kube/k3s-orbit"
COMPONENTS="${COMPONENTS:-all}"   # comma-separated or "all"

export KUBECONFIG="$KUBECONFIG_FILE"

# Colors
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
step()    { echo -e "\n${BLUE}==>${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }

enabled() {
  [[ "$COMPONENTS" == "all" ]] || echo "$COMPONENTS" | grep -qw "$1"
}

# ── Step 0: Fetch kubeconfig ───────────────────────────────────────────────────
step "Fetching kubeconfig from ${SERVER_IP}"
SERVER_IP="$SERVER_IP" SERVER_USER="$SERVER_USER" \
  SERVER_PASS="${SERVER_PASS:-}" SSH_KEY="${SSH_KEY:-}" \
  bash "$ORBIT_DIR/scripts/k3s-get-kubeconfig.sh"

step "Testing cluster connection"
kubectl cluster-info
kubectl get nodes
success "Connected to k3s cluster"

# ── Step 1: Disable k3s built-in Traefik (we use Kong) ────────────────────────
enabled "kong" && {
  step "Disabling k3s built-in Traefik ingress (we deploy Kong instead)"
  # k3s disables Traefik via HelmChartConfig
  kubectl apply -f - <<'EOF'
apiVersion: helm.cattle.io/v1
kind: HelmChartConfig
metadata:
  name: traefik
  namespace: kube-system
spec:
  valuesContent: |-
    deployment:
      replicas: 0
EOF
  success "Traefik disabled"
}

# ── Step 2: Namespaces ─────────────────────────────────────────────────────────
step "Creating namespaces"
kubectl apply -f "$ORBIT_DIR/infra/k3s/00-namespaces.yaml"
success "Namespaces created"

# ── Step 3: cert-manager ───────────────────────────────────────────────────────
enabled "cert-manager" && {
  step "Installing cert-manager"
  helm repo add jetstack https://charts.jetstack.io --force-update
  helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager --create-namespace \
    --set installCRDs=true \
    --set resources.requests.cpu=50m \
    --set resources.requests.memory=64Mi \
    --wait --timeout 5m
  success "cert-manager installed"

  # Self-signed ClusterIssuer for local dev
  kubectl apply -f - <<'EOF'
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
---
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: adports-internal-ca
spec:
  selfSigned: {}
EOF
  success "ClusterIssuers created (self-signed for k3s)"
}

# ── Step 4: Kong Ingress Controller ────────────────────────────────────────────
enabled "kong" && {
  step "Installing Kong ingress controller"
  helm repo add kong https://charts.konghq.com --force-update
  helm upgrade --install kong kong/kong \
    --namespace kong --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/kong/values.yaml" \
    --wait --timeout 5m
  KONG_IP=$(kubectl get svc -n kong kong-kong-proxy -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "$SERVER_IP")
  success "Kong installed — proxy IP: ${KONG_IP}"
  warn "Update SERVER_IP placeholders in infra/k3s/kong/values.yaml and infra/k3s/keycloak/values.yaml with: ${SERVER_IP}"
}

# ── Step 5: CloudNativePG Operator + Cluster ───────────────────────────────────
enabled "postgres" && {
  step "Installing CloudNativePG operator"
  helm repo add cnpg https://cloudnative-pg.github.io/charts --force-update
  helm upgrade --install cnpg cnpg/cloudnative-pg \
    --namespace cnpg-system --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/cloudnativepg/values.yaml" \
    --wait --timeout 5m
  success "CloudNativePG operator installed"

  step "Creating PostgreSQL cluster secrets"
  kubectl -n ai-portal-data create secret generic orbit-postgres-app-secret \
    --from-literal=username=orbit_app \
    --from-literal=password=orbit-pg-password \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl -n ai-portal-data create secret generic keycloak-db-creds \
    --from-literal=KC_DB_PASSWORD=orbit-pg-password \
    --dry-run=client -o yaml | kubectl apply -f -

  step "Deploying PostgreSQL cluster"
  kubectl apply -f "$ORBIT_DIR/infra/k3s/cloudnativepg/cluster.yaml"
  echo "Waiting for PostgreSQL to be ready (this may take 2-3 minutes)..."
  kubectl -n ai-portal-data wait cluster/orbit-postgres \
    --for=condition=Ready --timeout=5m 2>/dev/null || \
    kubectl -n ai-portal-data get cluster orbit-postgres
  success "PostgreSQL cluster deployed"
}

# ── Step 6: Vault ──────────────────────────────────────────────────────────────
enabled "vault" && {
  step "Installing HashiCorp Vault"
  helm repo add hashicorp https://helm.releases.hashicorp.com --force-update
  helm upgrade --install vault hashicorp/vault \
    --namespace vault --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/vault/values.yaml" \
    --wait --timeout 5m
  success "Vault installed"
  echo ""
  warn "MANUAL STEPS REQUIRED for Vault:"
  echo "  1. Initialize Vault:  kubectl -n vault exec vault-0 -- vault operator init"
  echo "  2. Unseal Vault (3x): kubectl -n vault exec vault-0 -- vault operator unseal <key>"
  echo "  3. Bootstrap:         VAULT_ADDR=http://${SERVER_IP}:30082 VAULT_TOKEN=<root> bash scripts/vault-bootstrap.sh"
  echo "  Access Vault UI:      http://${SERVER_IP}:30082"
}

# ── Step 7: Keycloak ───────────────────────────────────────────────────────────
enabled "keycloak" && {
  step "Installing Keycloak"

  # Create db creds secret
  kubectl -n ai-portal create secret generic keycloak-db-creds \
    --from-literal=KC_DB_PASSWORD=orbit-pg-password \
    --dry-run=client -o yaml | kubectl apply -f -

  helm repo add bitnami https://charts.bitnami.com/bitnami --force-update
  helm upgrade --install keycloak bitnami/keycloak \
    --namespace ai-portal \
    -f "$ORBIT_DIR/infra/k3s/keycloak/values.yaml" \
    --set "extraEnvVars[0].value=${SERVER_IP}" \
    --wait --timeout 8m
  success "Keycloak installed"
  echo "  Access: http://${SERVER_IP}:30180  (admin / orbit-keycloak)"
  warn "Create realm 'ai-portal' and clients: argocd, grafana, litellm, portal-api"
}

# ── Step 8: Strimzi + Kafka ────────────────────────────────────────────────────
enabled "kafka" && {
  step "Installing Strimzi Kafka Operator"
  helm repo add strimzi https://strimzi.io/charts/ --force-update
  helm upgrade --install strimzi-kafka-operator strimzi/strimzi-kafka-operator \
    --namespace kafka --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/kafka/operator-values.yaml" \
    --wait --timeout 5m
  success "Strimzi operator installed"

  step "Deploying Kafka cluster (single-node)"
  kubectl apply -f "$ORBIT_DIR/infra/k3s/kafka/kafka-cluster.yaml"
  echo "Waiting for Kafka to be ready (may take 3-5 minutes)..."
  kubectl -n kafka wait kafka/orbit-kafka \
    --for=condition=Ready --timeout=8m 2>/dev/null || \
    kubectl -n kafka get kafka orbit-kafka
  success "Kafka cluster deployed"
}

# ── Step 9: EventStoreDB ───────────────────────────────────────────────────────
enabled "eventstore" && {
  step "Installing EventStoreDB"
  helm repo add eventstore https://eventstore.github.io/EventStore.Charts --force-update
  helm upgrade --install eventstore eventstore/eventstore \
    --namespace eventstore --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/eventstore/values.yaml" \
    --wait --timeout 5m
  success "EventStoreDB installed"
}

# ── Step 10: Temporal ──────────────────────────────────────────────────────────
enabled "temporal" && {
  step "Installing Temporal workflow engine"
  helm repo add temporalio https://temporalio.github.io/helm-charts --force-update
  helm upgrade --install temporal temporalio/temporal \
    --namespace temporal --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/temporal/values.yaml" \
    --wait --timeout 8m
  success "Temporal installed"
  echo "  Access Temporal UI: http://${SERVER_IP}:30088"
}

# ── Step 11: Observability Stack ───────────────────────────────────────────────
enabled "observability" && {
  step "Installing kube-prometheus-stack (Prometheus + Grafana)"
  helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update
  helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
    --namespace monitoring --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/observability/prometheus-grafana-values.yaml" \
    --wait --timeout 8m
  success "Prometheus + Grafana installed"
  echo "  Access Grafana: http://${SERVER_IP}:30030  (admin / orbit-admin)"

  step "Installing Loki"
  helm repo add grafana https://grafana.github.io/helm-charts --force-update
  helm upgrade --install loki grafana/loki \
    --namespace monitoring \
    -f "$ORBIT_DIR/infra/k3s/observability/loki-values.yaml" \
    --wait --timeout 5m
  success "Loki installed"

  step "Installing Tempo"
  helm upgrade --install tempo grafana/tempo \
    --namespace monitoring \
    -f "$ORBIT_DIR/infra/k3s/observability/tempo-values.yaml" \
    --wait --timeout 5m
  success "Tempo installed"

  step "Installing OpenTelemetry Collector"
  helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts --force-update
  helm upgrade --install otel-collector open-telemetry/opentelemetry-collector \
    --namespace monitoring \
    -f "$ORBIT_DIR/infra/k3s/observability/otel-collector-values.yaml" \
    --wait --timeout 5m
  success "OTel Collector installed"
}

# ── Step 12: LiteLLM Gateway ───────────────────────────────────────────────────
enabled "litellm" && {
  step "Deploying LiteLLM Gateway"

  kubectl -n litellm create secret generic litellm-env \
    --from-literal=LITELLM_MASTER_KEY=sk-orbit-master-key \
    --from-literal=LITELLM_DB_URL="postgresql://orbit_app:orbit-pg-password@orbit-postgres-rw.ai-portal-data.svc.cluster.local:5432/ai_portal" \
    --from-literal=AZURE_OPENAI_ENDPOINT="" \
    --from-literal=AZURE_OPENAI_KEY="" \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl apply -f "$ORBIT_DIR/infra/k3s/litellm/deployment.yaml"
  success "LiteLLM Gateway deployed"
}

# ── Step 13: OpenFGA ───────────────────────────────────────────────────────────
enabled "openfga" && {
  step "Deploying OpenFGA"

  kubectl -n ai-portal create secret generic orbit-openfga-env \
    --from-literal=postgres_uri="postgresql://orbit_app:orbit-pg-password@orbit-postgres-rw.ai-portal-data.svc.cluster.local:5432/ai_portal?sslmode=disable" \
    --dry-run=client -o yaml | kubectl apply -f -

  kubectl apply -f "$ORBIT_DIR/infra/k3s/openfga/openfga.yaml"
  success "OpenFGA deployed"
}

# ── Step 14: HPA ──────────────────────────────────────────────────────────────
enabled "hpa" && {
  step "Applying HPAs"
  kubectl apply -f "$ORBIT_DIR/infra/k3s/hpa.yaml"
  success "HPAs applied (minReplicas=1 for single-node k3s)"
}

# ── Step 15: ArgoCD ────────────────────────────────────────────────────────────
enabled "argocd" && {
  step "Installing ArgoCD"
  helm repo add argo https://argoproj.github.io/argo-helm --force-update
  helm upgrade --install argocd argo/argo-cd \
    --namespace argocd --create-namespace \
    -f "$ORBIT_DIR/infra/k3s/argocd/values.yaml" \
    --wait --timeout 8m
  success "ArgoCD installed"
  echo "  Access ArgoCD: http://${SERVER_IP}:30080"
  ARGOCD_PASS=$(kubectl -n argocd get secret argocd-initial-admin-secret \
    -o jsonpath='{.data.password}' 2>/dev/null | base64 -d || echo "(not yet generated)")
  echo "  Initial admin password: ${ARGOCD_PASS}"
}

# ── Step 16: Network Policies ─────────────────────────────────────────────────
enabled "netpol" && {
  step "Applying NetworkPolicies"
  kubectl apply -f "$ORBIT_DIR/infra/k3s/network-policies.yaml"
  warn "NetworkPolicies applied — only enforced if using Cilium/Calico CNI (not default Flannel)"
}

# ── Summary ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  ORBIT k3s Deployment Complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════${NC}"
echo ""
echo "  Server IP     : ${SERVER_IP}"
echo "  Kubeconfig    : ${KUBECONFIG_FILE}"
echo ""
echo "  Service             URL"
echo "  ──────────────────  ─────────────────────────────────"
echo "  ArgoCD              http://${SERVER_IP}:30080"
echo "  Vault UI            http://${SERVER_IP}:30082"
echo "  Keycloak            http://${SERVER_IP}:30180"
echo "  Grafana             http://${SERVER_IP}:30030"
echo "  Temporal UI         http://${SERVER_IP}:30088"
echo "  Kong Proxy          http://${SERVER_IP}  (ports 80/443)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Initialize & unseal Vault (see step 6 output above)"
echo "  2. Run: VAULT_ADDR=http://${SERVER_IP}:30082 VAULT_TOKEN=<token> bash scripts/vault-bootstrap.sh"
echo "  3. Configure Keycloak realm 'ai-portal' at http://${SERVER_IP}:30180"
echo "  4. Update REPLACE_WITH_SERVER_IP in infra/k3s/kong/values.yaml and redeploy Kong"
echo "  5. Deploy application services: kubectl apply -f src/<service>/k8s/"
echo ""
