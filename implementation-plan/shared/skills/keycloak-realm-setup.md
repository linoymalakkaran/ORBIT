# Skill: Keycloak Realm Setup

## Skill ID
`keycloak-realm-setup`

## Version
`1.0.0`

## Used By
- Phase 01 (Infra Squad — initial Portal realm)
- Phase 02 (Core Data layer — realm per project type)
- Phase 08 (Keycloak MCP Server — realm provisioning tool)
- Backend Specialist Agent (new project Keycloak wiring)

## Description
End-to-end guide for creating and configuring a Keycloak realm for an AD Ports service. Covers realm creation, client registration, role model, group-to-role mapping, OIDC configuration, brute-force protection, and SCIM provisioning hooks.

---

## Skill Inputs

```json
{
  "realmName": "string",          // e.g. "dgd", "mpay", "portal"
  "serviceName": "string",        // e.g. "DGD Declaration Service"
  "clientIds": ["string"],        // e.g. ["dgd-ui", "dgd-api"]
  "roles": ["string"],            // e.g. ["customs_officer", "shipper", "supervisor"]
  "adminEmail": "string",
  "environment": "dev|staging|prod"
}
```

---

## Output Artefacts

```
keycloak/
├── realm-export.json              ← Full realm configuration (validated against adports-keycloak-realm.schema.json)
├── clients/
│   ├── {clientId}-client.json    ← Per-client configuration
│   └── ...
├── roles/
│   └── realm-roles.json          ← Role definitions + composite roles
├── groups/
│   └── groups.json               ← AD sync groups with role mappings
└── setup.sh                      ← Admin CLI script for headless provisioning
```

---

## Step-by-Step Implementation

### Step 1 — Create the Realm

```json
// realm-export.json skeleton (populate fields per adports-keycloak-realm.schema.json)
{
  "realm": "{realmName}",
  "enabled": true,
  "displayName": "AD Ports — {serviceName}",
  "sslRequired": "all",
  "registrationAllowed": false,
  "bruteForceProtected": true,
  "permanentLockout": false,
  "maxFailureWaitSeconds": 900,
  "passwordPolicy": "length(12) and notUsername and specialChars(1) and upperCase(1) and lowerCase(1) and digits(1)",
  "otpPolicyType": "totp",
  "otpPolicyPeriod": 30,
  "accessTokenLifespan": 300,
  "ssoSessionMaxLifespan": 28800
}
```

### Step 2 — Register Clients

Every service has two clients: a **public** frontend client and a **confidential** backend client.

```json
// clients/dgd-ui-client.json
{
  "clientId": "{realmName}-ui",
  "name": "{serviceName} UI",
  "enabled": true,
  "publicClient": true,
  "standardFlowEnabled": true,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false,
  "redirectUris": [
    "https://{realmName}.adports.ae/*",
    "https://{realmName}-dev.adports.ae/*"
  ],
  "webOrigins": [
    "https://{realmName}.adports.ae",
    "https://{realmName}-dev.adports.ae"
  ],
  "attributes": {
    "pkce.code.challenge.method": "S256"
  }
}

// clients/dgd-api-client.json  (machine-to-machine)
{
  "clientId": "{realmName}-api",
  "name": "{serviceName} API",
  "enabled": true,
  "publicClient": false,
  "serviceAccountsEnabled": true,
  "standardFlowEnabled": false,
  "implicitFlowEnabled": false,
  "directAccessGrantsEnabled": false
}
```

### Step 3 — Define Realm Roles

```json
{
  "roles": {
    "realm": [
      {
        "name": "platform_admin",
        "description": "Platform administrator — full access to Portal admin functions"
      },
      {
        "name": "{realmName}_supervisor",
        "description": "Supervisor role — approve, reject, manage team"
      },
      {
        "name": "{realmName}_operator",
        "description": "Standard operator — create and submit"
      },
      {
        "name": "{realmName}_readonly",
        "description": "Read-only — view only"
      }
    ]
  }
}
```

### Step 4 — Create Groups for AD Sync

Map Azure AD groups to Keycloak groups, then to roles via group-to-role mapper.

```json
{
  "groups": [
    {
      "name": "ad-portal-{realmName}-supervisors",
      "realmRoles": ["{realmName}_supervisor"],
      "attributes": {
        "ad_group": ["CN=AI-Portal-{RealmName}-Supervisors,OU=Groups,DC=adports,DC=ae"]
      }
    },
    {
      "name": "ad-portal-{realmName}-operators",
      "realmRoles": ["{realmName}_operator"],
      "attributes": {
        "ad_group": ["CN=AI-Portal-{RealmName}-Operators,OU=Groups,DC=adports,DC=ae"]
      }
    }
  ]
}
```

### Step 5 — Configure OIDC Token Claims

Add a protocol mapper to include AD groups and Portal roles in the JWT:

```json
{
  "protocolMappers": [
    {
      "name": "portal-roles",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-usermodel-realm-role-mapper",
      "config": {
        "claim.name": "roles",
        "jsonType.label": "String",
        "multivalued": "true",
        "access.token.claim": "true",
        "id.token.claim": "true",
        "userinfo.token.claim": "true"
      }
    },
    {
      "name": "portal-groups",
      "protocol": "openid-connect",
      "protocolMapper": "oidc-group-membership-mapper",
      "config": {
        "claim.name": "groups",
        "full.path": "false",
        "access.token.claim": "true",
        "id.token.claim": "false",
        "userinfo.token.claim": "false"
      }
    }
  ]
}
```

### Step 6 — Headless Provisioning Script

```bash
#!/usr/bin/env bash
# setup.sh — Idempotent Keycloak realm provisioning
set -euo pipefail

KC_BASE="${KEYCLOAK_URL:-https://auth.adports.ae}"
KC_ADMIN="${KEYCLOAK_ADMIN:-admin}"
KC_PASS="${KEYCLOAK_ADMIN_PASSWORD}"   # From Vault
REALM="${REALM_NAME}"

# Get admin token
TOKEN=$(curl -s -X POST "${KC_BASE}/realms/master/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password&client_id=admin-cli&username=${KC_ADMIN}&password=${KC_PASS}" \
  | jq -r '.access_token')

# Check if realm exists
EXISTING=$(curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${KC_BASE}/admin/realms/${REALM}")

if [[ "${EXISTING}" == "404" ]]; then
  echo "Creating realm ${REALM}..."
  curl -s -X POST "${KC_BASE}/admin/realms" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d @realm-export.json
  echo "Realm ${REALM} created."
else
  echo "Realm ${REALM} already exists — skipping creation."
fi

# Import clients (idempotent via client_id check)
for CLIENT_FILE in clients/*.json; do
  CLIENT_ID=$(jq -r '.clientId' "${CLIENT_FILE}")
  EXISTING_CLIENT=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
    "${KC_BASE}/admin/realms/${REALM}/clients?clientId=${CLIENT_ID}" | jq length)
  if [[ "${EXISTING_CLIENT}" == "0" ]]; then
    echo "Registering client ${CLIENT_ID}..."
    curl -s -X POST "${KC_BASE}/admin/realms/${REALM}/clients" \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d @"${CLIENT_FILE}"
  else
    echo "Client ${CLIENT_ID} already exists — skipping."
  fi
done

echo "Realm setup complete."
```

---

## Keycloak MCP Server Integration

When the Backend Specialist Agent provisions a new project, it calls the Keycloak MCP Server:

```python
# Via MCP tool call
await mcp.call_tool("keycloak", "provision_realm", {
    "realm_name": intent.project_id,
    "service_name": intent.project_name,
    "client_ids": [f"{intent.project_id}-ui", f"{intent.project_id}-api"],
    "roles": intent.roles or ["operator", "supervisor", "readonly"],
    "environment": "dev"
})
```

---

## Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC1 | Realm exists and is enabled in Keycloak admin UI |
| AC2 | SSL required = "all"; registration disabled; brute-force protected |
| AC3 | Both clients registered with correct redirect URIs |
| AC4 | `platform_admin` role exists and is assignable |
| AC5 | PKCE S256 enabled on public client |
| AC6 | Token claims include `roles` array from realm |
| AC7 | `setup.sh` is idempotent — running twice produces no errors |
| AC8 | Realm configuration validates against `adports-keycloak-realm.schema.json` |
| AC9 | Access token lifespan ≤ 300 seconds |
| AC10 | Admin password sourced from Vault (never hardcoded) |

---

## Common Mistakes

| Mistake | Consequence | Fix |
|---------|-------------|-----|
| `implicitFlowEnabled: true` | Security vulnerability (token in URL fragment) | Always `false` |
| `directAccessGrantsEnabled: true` in prod | Allows password grant — bypasses MFA | Only for test automation |
| Wildcard `redirectUris: ["*"]` | Any site can receive tokens (XSS risk) | List explicit URIs |
| `accessTokenLifespan > 300` | Long-lived tokens hard to revoke | Keep ≤ 5 minutes |
| Exporting secrets in realm export | Credentials leak to Git | Use `--optimized` export flag; scrub before committing |

---

*Keycloak Realm Setup Skill — AD Ports AI Portal — v1.0.0 — Owner: Infra Squad*
