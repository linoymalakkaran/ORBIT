# Skill: Postman/Newman AD Ports Baseline

## Skill ID
`postman-newman-adports-baseline`

## Description
Generates a Postman collection + environment files for an AD Ports service from its OpenAPI specification. Includes BRD integration scenarios, Vault-backed secret resolution, and Newman CI stage configuration.

## When To Use
- Creating API integration tests for a new .NET service.
- Running smoke tests against a deployed service environment.
- Validating SINTECE or other external integration flows using WireMock.

---

## Inputs Required

```json
{
  "serviceName": "string — e.g. dgd-declaration-service",
  "openApiSpecPath": "string — path to OpenAPI YAML",
  "environments": ["dev", "staging", "production"],
  "integrationScenarios": [
    {
      "id": "INT-DGD-001",
      "description": "string — end-to-end flow description",
      "steps": [
        { "request": "POST /declarations", "expectedStatus": 201 },
        { "request": "GET /declarations/{{declarationId}}", "expectedStatus": 200 }
      ]
    }
  ],
  "externalMocks": ["sintece", "ministry-of-economy"]
}
```

---

## Output Structure

```
postman/
├── collections/
│   └── {service-name}.postman_collection.json
├── environments/
│   ├── dev.json
│   ├── staging.json
│   └── production.json      — Secrets resolved from Vault at runtime
├── wiremock/
│   └── mappings/            — Mock responses for external dependencies
│       ├── sintece-*.json
│       └── moe-*.json
└── newman.config.js         — Newman CLI options
```

---

## Key Collection Features

- **Pre-request script**: Fetches access token from Keycloak (client credentials or password grant for test user).
- **Test scripts**: Assert status code, response schema (using Ajv), and business rules.
- **Variable chaining**: Response values (IDs, references) automatically set as variables for subsequent requests.
- **Integration scenario folders**: Each BRD integration scenario is a separate Postman folder with ordered requests.
- **WireMock mappings**: For every external system in `externalMocks`, generates a WireMock mapping file.

---

## Newman CI Stage

```yaml
# Generated and added to .gitlab-ci.yml by DevOps Agent
newman-integration-test:
  stage: integration-test
  image: postman/newman:6
  services:
    - name: wiremock/wiremock:latest
      alias: sintece-mock
      variables:
        WIREMOCK_OPTIONS: "--port 8080 --root-dir /mappings"
  script:
    - newman run postman/collections/${SERVICE_NAME}.postman_collection.json
        -e postman/environments/dev.json
        --env-var "baseUrl=${API_BASE_URL}"
        --env-var "accessToken=${CI_TEST_TOKEN}"
        --reporter-junit-export results/newman-results.xml
        --bail
```

---

## Acceptance Criteria

- [ ] `newman run collection.json -e dev.json` passes with 0 failures.
- [ ] All BRD integration scenarios covered.
- [ ] Secrets NOT stored in collection or environment files (resolved from Vault).
- [ ] WireMock mappings allow full integration flow without real external systems.
- [ ] Newman CI stage runs on every merge request.

---

## References

- [Phase 17 — Integration Test Agent](../../phases/phase-17/phase-17.md)
- [Phase 09 — Postman/Newman MCP Server](../../phases/phase-09/phase-09.md)

---

*shared/skills/postman-newman-adports-baseline.md — AI Portal — v1.0*
