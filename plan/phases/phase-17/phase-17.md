# Phase 17 — Integration Test Agent (Postman/Newman)

## Summary

Implement the **Integration Test Agent** — generates Postman collections from OpenAPI specifications and BRD integration scenarios, with environment files for dev/staging/production. The agent also generates Newman CLI execution configs, environment-specific test data, and integrates with the CI pipeline via DevOps Agent. Tests are stored in the Pipeline Ledger as compliance evidence.

---

## Objectives

1. Implement OpenAPI-to-Postman collection generator.
2. Implement BRD integration scenario mapper (links acceptance criteria to API calls).
3. Implement environment file generator (dev/staging/prod with secret masking).
4. Implement environment-specific test data generator.
5. Implement Newman CLI config generator.
6. Implement CI stage additions (Newman test stages).
7. Implement test result upload to Portal API.
8. Implement `adports-ai test integration` CLI command.
9. Wire Integration Test Agent to Orchestrator framework.
10. Implement SINTECE external integration test harness (WireMock mock).

---

## Prerequisites

- Phase 09 (Postman/Newman MCP server).
- Phase 12 (Backend Agent — generated services with OpenAPI specs).
- Phase 15 (DevOps Agent — CI pipeline to extend).
- Phase 03 (Portal API — test result endpoints).

---

## Duration

**2 weeks** (runs in parallel with Phase 16)

**Squad:** QA & Test Squad (1 senior QA + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Postman collection | Generated collection contains all OpenAPI endpoints with examples |
| D2 | BRD scenario mapping | All BRD integration scenarios have corresponding test folders |
| D3 | Environment files | dev/staging/prod env files generated; secrets from Vault |
| D4 | Newman config | `newman run collection.json -e dev.json` passes with 0 failures |
| D5 | CI integration | Newman stage in GitLab CI; results in test report |
| D6 | WireMock harness | SINTECE external service mocked; integration flow passes |
| D7 | CLI command | `adports-ai test integration --project=dgd --env=dev` runs tests |
| D8 | Portal upload | Test results visible in Portal project dashboard |
| D9 | Ledger integration | Test execution event with pass/fail count in Ledger |
| D10 | Pact verify | Integration tests double as Pact provider verification |

---

## OpenAPI-to-Postman Collection Structure

```json
{
  "info": {
    "name": "DGD Declaration Service",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
  },
  "item": [
    {
      "name": "Declarations",
      "item": [
        {
          "name": "POST /declarations — Submit declaration (Happy path)",
          "request": {
            "method": "POST",
            "url": "{{baseUrl}}/api/declarations",
            "header": [
              { "key": "Authorization", "value": "Bearer {{accessToken}}" },
              { "key": "Content-Type", "value": "application/json" }
            ],
            "body": {
              "mode": "raw",
              "raw": "{{declarationPayload}}"
            }
          },
          "event": [
            {
              "listen": "test",
              "script": {
                "exec": [
                  "pm.test('Status is 201', () => pm.response.to.have.status(201));",
                  "pm.test('Has reference number', () => {",
                  "  const body = pm.response.json();",
                  "  pm.expect(body.referenceNumber).to.match(/^DGD-/);",
                  "  pm.environment.set('declarationId', body.id);",
                  "});"
                ]
              }
            }
          ]
        }
      ]
    }
  ],
  "variable": [
    { "key": "baseUrl", "value": "{{baseUrl}}" }
  ]
}
```

---

## Environment Files

```json
// Generated: environments/dev.json
{
  "name": "DGD Dev",
  "values": [
    { "key": "baseUrl", "value": "https://dev.api.adports.ae/dgd", "enabled": true },
    { "key": "keycloakUrl", "value": "https://auth.adports.ae/realms/portal", "enabled": true },
    { "key": "accessToken", "value": "{{FETCH_FROM_VAULT}}", "enabled": true, "type": "secret" },
    { "key": "declarationPayload", "value": "{\"cargoType\":\"GENERAL\",\"weight\":500,\"originPort\":\"AEJEA\",\"destinationPort\":\"AEFJR\"}", "enabled": true }
  ]
}
```

Secret values are resolved at runtime from Vault (never stored in git):

```javascript
// pre-request script for the collection
const vaultUrl = pm.environment.get('vaultUrl');
const tokenResponse = pm.sendRequest({
  url: `${vaultUrl}/v1/auth/approle/login`,
  method: 'POST',
  body: { mode: 'raw', raw: JSON.stringify({ role_id: pm.environment.get('vaultRoleId'), secret_id: pm.environment.get('vaultSecretId') }) }
});
pm.environment.set('accessToken', tokenResponse.json().auth.client_token);
```

---

## WireMock SINTECE Harness

```json
// wiremock/mappings/sintece-submit-mapping.json
{
  "request": {
    "method": "POST",
    "urlPattern": "/sintece/api/declarations/.*"
  },
  "response": {
    "status": 200,
    "headers": { "Content-Type": "application/json" },
    "jsonBody": {
      "customsDeclarationId": "SINT-{{randomValue type='UUID'}}",
      "status": "RECEIVED",
      "estimatedProcessingTime": "PT24H"
    },
    "transformers": ["response-template"]
  }
}
```

The WireMock container is started as a service in the CI pipeline for integration test stages.

---

## Newman GitLab CI Stage

```yaml
# Added to generated .gitlab-ci.yml by DevOps Agent (Phase 15)
newman-integration-test:
  stage: integration-test
  image: postman/newman:6
  services:
    - name: wiremock/wiremock:latest
      alias: sintece-mock
  before_script:
    - newman --version
  script:
    - newman run collections/${SERVICE_NAME}.postman_collection.json
        -e environments/dev.json
        --env-var "baseUrl=${API_BASE_URL}"
        --env-var "accessToken=${CI_TEST_TOKEN}"
        --reporter-junit-export results/newman-results.xml
        --bail  # Fail on first test failure
  artifacts:
    reports:
      junit: results/newman-results.xml
    when: always
  only: [main, merge_requests]
```

---

## CLI Command

```bash
# Developer runs integration tests locally
adports-ai test integration --project=dgd --env=dev

# Output:
# ✓ Connected to dev API at https://dev.api.adports.ae/dgd
# ✓ Retrieved access token from Vault
# Running 24 tests across 8 request groups...
# ✓ Declarations [6/6 passed]
# ✓ Fee calculation [4/4 passed]
# ✓ SINTECE integration [3/3 passed]
# ✓ Notifications [4/4 passed]
# ✓ Authentication [4/4 passed]
# ✗ Approval workflow [2/3 passed] - FAILED: Expected 403 when shipper approves own declaration
# Results uploaded to Portal project DGD-2025-001
# Summary: 23/24 passed (1 failed)
```

---

## Step-by-Step Execution Plan

### Week 1: Collection + Environment Generators

- [ ] Implement OpenAPI-to-Postman collection generator.
- [ ] Implement BRD scenario mapper (links AC to request sequences).
- [ ] Implement environment file generator (dev/staging/prod).
- [ ] Implement test data variable generator.
- [ ] Test: DGD OpenAPI → collection; `newman run` passes.

### Week 2: CI + WireMock + Agent Wiring

- [ ] Implement WireMock mapping generator for external dependencies.
- [ ] Implement Newman CI stage generator (adds to DevOps Agent output).
- [ ] Implement test result upload to Portal API.
- [ ] Implement `adports-ai test integration` CLI command.
- [ ] Implement `IntegrationTestAgentWorker` in Orchestrator framework.
- [ ] End-to-end test: DGD project → collection generated → Newman passes in CI.

---

## Gate Criterion

- DGD Postman collection generated from OpenAPI with all endpoints covered.
- `newman run` passes with 0 failures in dev environment.
- Newman CI stage runs in GitLab CI on merge request.
- WireMock SINTECE harness allows full integration flow to complete without real SINTECE.
- Test results visible in Portal project dashboard.
- Pipeline Ledger records test execution with pass/fail count.

---

*Phase 17 — Integration Test Agent (Postman/Newman) — AI Portal — v1.0*
