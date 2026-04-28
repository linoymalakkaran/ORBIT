#!/usr/bin/env bash
# create-harbor-secrets.sh — creates harbor-pull-secret in all required namespaces
# Usage: HARBOR_ROBOT_USER=... HARBOR_ROBOT_PASSWORD=... bash scripts/create-harbor-secrets.sh
set -euo pipefail

: "${HARBOR_ROBOT_USER:?HARBOR_ROBOT_USER required}"
: "${HARBOR_ROBOT_PASSWORD:?HARBOR_ROBOT_PASSWORD required}"

HARBOR_REGISTRY="harbor.ai.adports.ae"
NAMESPACES=(ai-portal ai-portal-data litellm temporal monitoring)

for ns in "${NAMESPACES[@]}"; do
  echo "==> Creating harbor-pull-secret in namespace: $ns"
  kubectl create namespace "$ns" --dry-run=client -o yaml | kubectl apply -f -
  kubectl create secret docker-registry harbor-pull-secret \
    --docker-server="$HARBOR_REGISTRY" \
    --docker-username="$HARBOR_ROBOT_USER" \
    --docker-password="$HARBOR_ROBOT_PASSWORD" \
    --namespace="$ns" \
    --dry-run=client -o yaml | kubectl apply -f -
  echo "  Done: $ns"
done

echo ""
echo "==> Harbor pull secrets created in all namespaces."
