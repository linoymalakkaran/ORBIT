# HashiCorp Vault Runbook

## Overview
ORBIT uses **HashiCorp Vault 1.17.3** via Helm + **Vault Agent Injector** for secret delivery.  
Namespace: `ai-portal-vault` | Dev: standalone | Prod: HA Raft 3 nodes.

---

## Access

| Item | Value |
|------|-------|
| Internal address | `http://vault.ai-portal-vault.svc.cluster.local:8200` |
| External (dev, port-forward) | `kubectl -n ai-portal-vault port-forward svc/vault 8200:8200` |
| UI | https://vault.ai.adports.ae |
| Root token | Stored securely after `vault operator init` — never committed to Git |

---

## Initialization & Unsealing

### Initialize (first time only)
```bash
kubectl -n ai-portal-vault exec -it vault-0 -- \
  vault operator init -key-shares=5 -key-threshold=3 \
  -format=json > /tmp/vault-init.json
# Store the 5 unseal keys and root token in a secure offline location!
```

### Unseal after pod restart
```bash
# Repeat with 3 of the 5 keys
kubectl -n ai-portal-vault exec -it vault-0 -- vault operator unseal <key1>
kubectl -n ai-portal-vault exec -it vault-0 -- vault operator unseal <key2>
kubectl -n ai-portal-vault exec -it vault-0 -- vault operator unseal <key3>
```

### Check seal status
```bash
kubectl -n ai-portal-vault exec -it vault-0 -- vault status
```

---

## Common Secret Operations

```bash
# Login (use AppRole in automation — root token only for admin)
export VAULT_ADDR=http://vault.ai-portal-vault.svc.cluster.local:8200
vault login $ROOT_TOKEN

# Write a secret
vault kv put secret/orbit/postgres password="changeme"

# Read a secret
vault kv get secret/orbit/postgres

# Delete a secret
vault kv delete secret/orbit/postgres
```

---

## Kubernetes Auth

Configure once after init:
```bash
vault auth enable kubernetes

vault write auth/kubernetes/config \
  kubernetes_host="https://kubernetes.default.svc.cluster.local" \
  kubernetes_ca_cert=@/var/run/secrets/kubernetes.io/serviceaccount/ca.crt \
  token_reviewer_jwt=@/var/run/secrets/kubernetes.io/serviceaccount/token

# Create policy
vault policy write orbit-app - <<EOF
path "secret/data/orbit/*" { capabilities = ["read"] }
EOF

# Create role
vault write auth/kubernetes/role/orbit-app \
  bound_service_account_names="orbit-app" \
  bound_service_account_namespaces="ai-portal-core,ai-portal-agents" \
  policies="orbit-app" ttl="1h"
```

---

## Vault Agent Injector Annotations (reference)

```yaml
vault.hashicorp.com/agent-inject: "true"
vault.hashicorp.com/role: "orbit-app"
vault.hashicorp.com/agent-inject-secret-db-creds: "secret/data/orbit/postgres"
vault.hashicorp.com/agent-inject-template-db-creds: |
  {{- with secret "secret/data/orbit/postgres" -}}
  DB_PASSWORD={{ .Data.data.password }}
  {{- end }}
```

---

## Raft Cluster Health (Prod)

```bash
kubectl -n ai-portal-vault exec -it vault-0 -- \
  vault operator raft list-peers
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `VaultSealed` | Vault pod restarted and needs unsealing | Run unseal procedure above |
| `VaultHA_Standby` | Active node changed | Check raft peers, re-elect if needed |
| `VaultTokenExpiry` | Orphaned tokens approaching TTL | Rotate AppRole credentials |
