#!/usr/bin/env bash
# =============================================================================
# k3s-get-kubeconfig.sh
# Fetches the kubeconfig from your remote k3s server and saves it locally.
# Requires: ssh, sshpass (for password auth) or SSH key
#
# Usage:
#   SERVER_IP=1.2.3.4 SERVER_PASS=mypassword ./scripts/k3s-get-kubeconfig.sh
#   SERVER_IP=1.2.3.4 SSH_KEY=~/.ssh/id_rsa ./scripts/k3s-get-kubeconfig.sh
# =============================================================================
set -euo pipefail

SERVER_IP="${SERVER_IP:?Set SERVER_IP=your.server.ip}"
SERVER_USER="${SERVER_USER:-root}"
KUBECONFIG_DIR="${HOME}/.kube"
KUBECONFIG_FILE="${KUBECONFIG_DIR}/k3s-orbit"

mkdir -p "$KUBECONFIG_DIR"
chmod 700 "$KUBECONFIG_DIR"

echo "==> Fetching kubeconfig from ${SERVER_USER}@${SERVER_IP} ..."

if [[ -n "${SSH_KEY:-}" ]]; then
  scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    "${SERVER_USER}@${SERVER_IP}:/etc/rancher/k3s/k3s.yaml" \
    "$KUBECONFIG_FILE"
elif [[ -n "${SERVER_PASS:-}" ]]; then
  # sshpass must be installed: apt install sshpass / brew install hudochenkov/sshpass/sshpass
  sshpass -p "$SERVER_PASS" scp \
    -o StrictHostKeyChecking=no \
    "${SERVER_USER}@${SERVER_IP}:/etc/rancher/k3s/k3s.yaml" \
    "$KUBECONFIG_FILE"
else
  echo "ERROR: Set either SSH_KEY or SERVER_PASS"
  exit 1
fi

# Replace 127.0.0.1 with the actual server IP so kubectl works remotely
sed -i.bak "s|127.0.0.1|${SERVER_IP}|g" "$KUBECONFIG_FILE"
sed -i.bak "s|https://localhost|https://${SERVER_IP}|g" "$KUBECONFIG_FILE"
chmod 600 "$KUBECONFIG_FILE"

echo ""
echo "==> Kubeconfig saved to: ${KUBECONFIG_FILE}"
echo ""
echo "==> Test connectivity:"
echo "    export KUBECONFIG=${KUBECONFIG_FILE}"
echo "    kubectl get nodes"
echo ""
echo "==> Or merge into default kubeconfig:"
echo "    KUBECONFIG=${KUBECONFIG_FILE}:~/.kube/config kubectl config view --flatten > /tmp/merged.yaml"
echo "    mv /tmp/merged.yaml ~/.kube/config"
