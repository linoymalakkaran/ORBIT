# Kong Ingress Controller Runbook

## Overview
ORBIT uses **Kong 3.8.0 + KIC 3.3.1** as the API gateway / ingress.  
Namespace: `ai-portal-system` | LoadBalancer IP assigned by MetalLB.

---

## Connection Details

| Item | Value |
|------|-------|
| Proxy (external) | MetalLB IP from `orbit-pool` range |
| Admin API (internal) | `kong-admin.ai-portal-system.svc.cluster.local:8001` |
| Admin GUI | https://kong-admin.ai.adports.ae |

---

## Common Operations

### Check proxy pod status
```bash
kubectl -n ai-portal-system get pods -l app.kubernetes.io/name=kong
kubectl -n ai-portal-system get svc -l app.kubernetes.io/name=kong
```

### Reload Kong configuration
Kong KIC is declarative — changes to `Ingress` / `KongPlugin` CRs are applied automatically.

### List all routes (via Admin API)
```bash
kubectl -n ai-portal-system port-forward svc/kong-admin 8001:8001 &
curl -s http://localhost:8001/routes | jq '.data[].name'
```

### Check a specific service
```bash
curl -s http://localhost:8001/services/<service-name> | jq .
```

### Kong Plugin: JWT auth
```yaml
apiVersion: configuration.konghq.com/v1
kind: KongPlugin
metadata:
  name: jwt-auth
  namespace: ai-portal-core
plugin: jwt
config:
  key_claim_name: sub
  secret_is_base64: false
```

---

## Adding an Ingress Rule

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: portal-api-ingress
  namespace: ai-portal-core
  annotations:
    konghq.com/strip-path: "false"
    konghq.com/plugins: "jwt-auth,rate-limit"
spec:
  ingressClassName: kong
  rules:
    - host: api.ai.adports.ae
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service: { name: portal-api, port: { number: 8080 } }
  tls:
    - hosts: [api.ai.adports.ae]
      secretName: orbit-wildcard-tls
```

---

## TLS Wildcard Certificate

cert-manager issues `orbit-wildcard-tls` in `ai-portal-system` using `adports-internal-ca`:
```bash
kubectl -n ai-portal-system get certificate orbit-wildcard-tls
kubectl -n ai-portal-system describe certificate orbit-wildcard-tls
```

---

## Alerts

| Alert | Meaning | Action |
|-------|---------|--------|
| `KongProxyDown` | Pod not ready | Describe pod, check logs |
| `KongHighLatency` | P99 > 2s | Review Kong routes, check upstream service |
| `KongHighErrorRate` | 5xx > 1% | Check upstream logs, review Kong plugin configs |
