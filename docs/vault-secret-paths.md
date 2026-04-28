# Vault secret path layout for ORBIT AI Portal
# All paths are under secret/orbit/

## Platform Infrastructure
secret/orbit/kubeconfig/dev          — TKG cluster kubeconfig (base64)
secret/orbit/kubeconfig/prod         — TKG cluster kubeconfig (base64)

## PostgreSQL
secret/orbit/postgres/superuser      — {username, password}
secret/orbit/postgres/app            — {username, password}  ← orbit_app role

## Redis
secret/orbit/redis/password          — {password}

## MinIO
secret/orbit/minio/root-creds        — {accessKey, secretKey}
secret/orbit/minio/app               — {accessKey, secretKey}

## Keycloak
secret/orbit/keycloak/admin-creds    — {username, password}
secret/orbit/keycloak/db-creds       — {username, password}
secret/orbit/keycloak/clients/portal-api  — {clientId, clientSecret}
secret/orbit/keycloak/clients/argocd      — {clientId, clientSecret}
secret/orbit/keycloak/clients/grafana     — {clientId, clientSecret}

## OpenFGA
secret/orbit/openfga/store           — {storeId, authorizationModelId}

## EventStoreDB
secret/orbit/eventstore/admin        — {username, password}

## Kafka
secret/orbit/kafka/producer          — {username, password}
secret/orbit/kafka/consumer          — {username, password}

## Portal API
secret/orbit/portal-api/jwt-signing  — {signingKey}

## Observability
secret/orbit/grafana/oidc            — {clientId, clientSecret}

## Rotation Policy
# Postgres  : 90-day automated rotation via Vault database secrets engine
# Redis     : 180-day manual rotation
# All OIDC  : 365-day; rotated before expiry via Keycloak client credentials endpoint
