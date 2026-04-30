# ORBIT on k3s — Deployment Guide

Deploy the full ORBIT AI Platform to a single Linux server running k3s, entirely from your local machine (Windows/Mac/Linux) using SSH.

---

## Prerequisites

### On your local machine
| Tool | Install |
|------|---------|
| `kubectl` | https://kubernetes.io/docs/tasks/tools/ |
| `helm` | https://helm.sh/docs/intro/install/ |
| `sshpass` | `apt install sshpass` / `brew install hudochenkov/sshpass/sshpass` / [Windows](https://github.com/dora-rs/sshpass-win) |
| `bash` | Git Bash (Windows), Terminal (Mac/Linux) |

### On your k3s server
k3s should already be installed. Verify:
```bash
ssh root@SERVER_IP "kubectl get nodes"
```

---

## Quick Start (3 commands)

```bash
# 1. Clone / cd into repo
cd /path/to/AI-Platform-Adports/v2

# 2. Deploy everything
SERVER_IP=1.2.3.4 SERVER_PASS=yourpassword bash scripts/deploy-k3s.sh

# 3. Access services in your browser (ports listed at end of script output)
```

---

## What Changed for k3s

| Component | Production (vSphere) | k3s Single-Node |
|-----------|---------------------|-----------------|
| **Storage** | `vsphere-csi` StorageClass | `local-path` (built-in k3s) |
| **Images** | `harbor.ai.adports.ae/orbit/*` | Public registries (Docker Hub, ghcr.io, quay.io) |
| **Kafka** | 3 brokers + 3 ZooKeepers | 1 broker + 1 ZooKeeper |
| **Replicas** | 2–3 everywhere | 1 everywhere |
| **Load Balancer** | MetalLB | k3s built-in ServiceLB (Klipper) |
| **Ingress** | Kong (LoadBalancer) | Kong (ServiceLB) — Traefik disabled |
| **NetworkPolicies** | Enforced (Calico) | Created but not enforced (Flannel default) |
| **HPA minReplicas** | 2 | 1 |
| **TLS** | cert-manager + internal CA | cert-manager self-signed |
| **Secrets** | Vault agent injection | K8s Secrets (Vault optional) |

---

## Directory Structure

```
infra/k3s/
├── 00-namespaces.yaml
├── hpa.yaml
├── network-policies.yaml
├── argocd/values.yaml
├── cloudnativepg/
│   ├── cluster.yaml
│   └── values.yaml
├── eventstore/values.yaml
├── kafka/
│   ├── kafka-cluster.yaml
│   └── operator-values.yaml
├── keycloak/values.yaml
├── kong/values.yaml
├── litellm/deployment.yaml
├── observability/
│   ├── loki-values.yaml
│   ├── otel-collector-values.yaml
│   ├── prometheus-grafana-values.yaml
│   └── tempo-values.yaml
├── openfga/openfga.yaml
├── temporal/values.yaml
└── vault/values.yaml

scripts/
├── k3s-get-kubeconfig.sh      # Fetch kubeconfig from server
├── deploy-k3s.sh              # Full deploy from local machine
└── vault-bootstrap-k3s.sh    # Vault init for k3s
```

---

## Deploy Individual Components

```bash
# Only deploy kafka + observability
COMPONENTS="kafka observability" SERVER_IP=1.2.3.4 SERVER_PASS=pass bash scripts/deploy-k3s.sh

# Available component names:
# cert-manager, kong, postgres, vault, keycloak, kafka,
# eventstore, temporal, observability, litellm, openfga, hpa, argocd, netpol
```

---

## Service Access URLs

After deployment, all services are accessible directly from your browser:

| Service | URL | Credentials |
|---------|-----|-------------|
| ArgoCD | `http://SERVER_IP:30080` | admin / (from secret) |
| Vault UI | `http://SERVER_IP:30082` | root token |
| Keycloak | `http://SERVER_IP:30180` | admin / orbit-keycloak |
| Grafana | `http://SERVER_IP:30030` | admin / orbit-admin |
| Temporal UI | `http://SERVER_IP:30088` | — |
| Kong Proxy | `http://SERVER_IP` | — |

---

## Post-Deploy Manual Steps

### 1. Initialize Vault
```bash
# On your local machine (after kubeconfig is fetched):
export KUBECONFIG=~/.kube/k3s-orbit

# Initialize
kubectl -n vault exec vault-0 -- vault operator init

# Unseal (run 3 times with 3 different unseal keys)
kubectl -n vault exec vault-0 -- vault operator unseal <unseal-key-1>
kubectl -n vault exec vault-0 -- vault operator unseal <unseal-key-2>
kubectl -n vault exec vault-0 -- vault operator unseal <unseal-key-3>

# Bootstrap
VAULT_ADDR=http://SERVER_IP:30082 VAULT_TOKEN=<root_token> \
  bash scripts/vault-bootstrap-k3s.sh
```

### 2. Configure Keycloak
1. Open `http://SERVER_IP:30180`
2. Log in as `admin / orbit-keycloak`
3. Create realm: `ai-portal`
4. Create clients: `argocd`, `grafana`, `portal-api`, `litellm`

### 3. Deploy Application Services
```bash
export KUBECONFIG=~/.kube/k3s-orbit
kubectl apply -f src/portal-api/k8s/
kubectl apply -f src/orchestrator/k8s/
# ... etc for other services
```

---

## NetworkPolicies with Cilium (Optional)

If you want to enforce NetworkPolicies, reinstall k3s with Cilium:

```bash
# On the server — reinstall k3s with Flannel disabled
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--flannel-backend=none --disable-network-policy" sh -

# Install Cilium
helm repo add cilium https://helm.cilium.io/
helm install cilium cilium/cilium --namespace kube-system \
  --set operator.replicas=1

# Then apply network policies
kubectl apply -f infra/k3s/network-policies.yaml
```

---

## Troubleshooting

```bash
export KUBECONFIG=~/.kube/k3s-orbit

# Check all pods
kubectl get pods -A

# Check a failing pod
kubectl describe pod -n <namespace> <pod-name>
kubectl logs -n <namespace> <pod-name>

# Check storage
kubectl get pvc -A

# Check k3s server logs (on the server)
ssh root@SERVER_IP "journalctl -u k3s -f"
```
