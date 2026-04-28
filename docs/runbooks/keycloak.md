# Keycloak Runbook

## Overview
ORBIT uses **Keycloak 25** as the identity provider.  
Namespace: `ai-portal-keycloak` | Realm: `ai-portal` | Domain: `auth.ai.adports.ae`

---

## Access

| Item | Value |
|------|-------|
| Admin console | https://auth.ai.adports.ae/admin |
| OIDC discovery | https://auth.ai.adports.ae/realms/ai-portal/.well-known/openid-configuration |
| Admin credentials | From Vault: `secret/orbit/keycloak/admin-creds` |

---

## Common Operations

### Check pod health
```bash
kubectl -n ai-portal-keycloak get pods -l app.kubernetes.io/name=keycloak
kubectl -n ai-portal-keycloak logs -l app.kubernetes.io/name=keycloak -f
```

### Export realm configuration
```bash
kubectl -n ai-portal-keycloak exec -it \
  $(kubectl -n ai-portal-keycloak get pod -l app.kubernetes.io/name=keycloak -o name | head -1) \
  -- /opt/keycloak/bin/kc.sh export \
     --dir /tmp/export --realm ai-portal
kubectl -n ai-portal-keycloak cp \
  $(kubectl -n ai-portal-keycloak get pod -l app.kubernetes.io/name=keycloak -o name | head -1 | cut -d/ -f2):/tmp/export/ai-portal-realm.json \
  ./ai-portal-realm.json
```

### Import realm configuration
```bash
kubectl -n ai-portal-keycloak cp ./ai-portal-realm.json \
  <keycloak-pod>:/tmp/ai-portal-realm.json
kubectl -n ai-portal-keycloak exec -it <keycloak-pod> -- \
  /opt/keycloak/bin/kc.sh import --file /tmp/ai-portal-realm.json
```

---

## OIDC Client Registration

Clients to register in `ai-portal` realm:

| Client ID | Purpose |
|-----------|---------|
| `portal-ui` | Angular SPA (public PKCE) |
| `portal-api` | .NET backend (confidential) |
| `argocd` | ArgoCD SSO |
| `grafana` | Grafana SSO |

---

## Adding a New Client (CLI)

```bash
# Port-forward first
kubectl -n ai-portal-keycloak port-forward svc/keycloak 8080:80 &

# Get admin token
ACCESS_TOKEN=$(curl -s \
  -d "client_id=admin-cli" \
  -d "username=admin" \
  -d "password=$KC_PASS" \
  -d "grant_type=password" \
  "http://localhost:8080/realms/master/protocol/openid-connect/token" \
  | jq -r '.access_token')

# Create client
curl -s -X POST http://localhost:8080/admin/realms/ai-portal/clients \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"clientId":"my-service","enabled":true,"publicClient":false}'
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `KeycloakDown` | Pod not ready | Check DB connectivity (Postgres), check logs |
| `KeycloakHighLoginFailures` | Brute force attempt | Review Keycloak events log in admin UI |
| `KeycloakDBConnectionFailed` | Cannot reach Postgres | Check CNPG cluster status |
