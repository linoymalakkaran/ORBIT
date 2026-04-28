# Instructions — Phase 14: QA Agent

> Add this file to your IDE's custom instructions when building or extending the QA Agent.

---

## Context

You are building the **AD Ports QA Agent** — an AI agent that generates end-to-end Playwright tests, Newman (Postman) API test collections, and Testcontainers integration tests for generated services. The QA Agent runs after Backend and Frontend Agents have produced code, and outputs test suites that run in CI without manual configuration.

---

## Playwright E2E Generation Pattern

```typescript
// Generated Playwright test structure for every Angular feature
import { test, expect } from '@playwright/test';
import { LoginPage }     from '../pages/login.page';
import { DeclarationFormPage } from '../pages/declaration-form.page';

test.describe('Declaration Form — Submit Dangerous Goods Declaration', () => {

  test.beforeEach(async ({ page }) => {
    const login = new LoginPage(page);
    await login.loginAs('senior_developer');
  });

  test('AC1 — Submits valid declaration and redirects to list', async ({ page }) => {
    const form = new DeclarationFormPage(page);
    await form.navigate();

    await form.fillCargoType('Flammable Liquid');
    await form.fillWeight(1500);
    await form.fillOriginPort('AEAUH');
    await form.submit();

    await expect(page).toHaveURL('/declarations');
    await expect(page.locator('[data-testid="success-toast"]')).toBeVisible();
  });

  test('AC2 — Shows validation error for missing cargo type', async ({ page }) => {
    const form = new DeclarationFormPage(page);
    await form.navigate();

    await form.fillWeight(1500);
    await form.submit();

    await expect(page.locator('[data-testid="cargo-type-error"]')).toBeVisible();
    await expect(page).toHaveURL('/declarations/new');  // Did not navigate away
  });

  test('AC3 — Requires authentication (redirects unauthenticated)', async ({ browser }) => {
    const context = await browser.newContext({ storageState: undefined });
    const page    = await context.newPage();
    await page.goto('/declarations/new');
    await expect(page).toHaveURL(/.*keycloak.*\/login/);
  });
});
```

## Page Object Model Requirements

```typescript
// Every feature gets a Page Object class
// File: tests/e2e/pages/declaration-form.page.ts
export class DeclarationFormPage {
  constructor(private page: Page) {}

  async navigate() {
    await this.page.goto('/declarations/new');
  }

  async fillCargoType(value: string) {
    await this.page.getByTestId('cargo-type-input').fill(value);
  }

  async submit() {
    await this.page.getByTestId('submit-button').click();
  }
}

// Angular components MUST have data-testid attributes:
// <input pInputText data-testid="cargo-type-input" formControlName="cargoType" />
// The QA Agent will fail if it cannot find data-testid attributes.
```

## Newman API Test Generation

```json
// Generated Postman collection (subset)
{
  "info": { "name": "Declarations API — Integration Tests" },
  "item": [
    {
      "name": "POST /api/declarations — valid payload → 201",
      "request": {
        "method": "POST",
        "url": "{{baseUrl}}/api/declarations",
        "header": [{ "key": "Authorization", "value": "Bearer {{token}}" }],
        "body": {
          "mode": "raw",
          "raw": "{ \"cargoType\": \"Flammable Liquid\", \"weight\": 1500, \"originPort\": \"AEAUH\" }"
        }
      },
      "event": [{
        "listen": "test",
        "script": {
          "exec": [
            "pm.test('Status is 201', () => pm.response.to.have.status(201));",
            "pm.test('Has id', () => pm.expect(pm.response.json().id).to.be.a('string'));",
            "pm.environment.set('declarationId', pm.response.json().id);"
          ]
        }
      }]
    }
  ]
}
```

## Testcontainers Integration Test Pattern

```csharp
// Generated integration test using Testcontainers
public class DeclarationEndpointsTests : IAsyncLifetime
{
    private readonly PostgreSqlContainer _postgres =
        new PostgreSqlBuilder().WithDatabase("declarations_test").Build();

    public async Task InitializeAsync()
    {
        await _postgres.StartAsync();
        // Use factory with test connection string
    }

    [Fact]
    public async Task CreateDeclaration_ValidPayload_Returns201()
    {
        var client  = _factory.CreateAuthenticatedClient("senior_developer");
        var payload = new { CargoType = "Flammable Liquid", Weight = 1500, OriginPort = "AEAUH" };

        var response = await client.PostAsJsonAsync("/api/declarations", payload);

        response.StatusCode.Should().Be(HttpStatusCode.Created);
        var result = await response.Content.ReadFromJsonAsync<DeclarationDto>();
        result!.Id.Should().NotBeEmpty();
    }
}
```

## Acceptance Criteria Coverage

The QA Agent MUST generate at least one test per acceptance criterion (AC) from the WorkPackage:
- Parse `acceptance_criteria` from the WorkPackage
- Map each `AC-XXX-NNN` to a `test()` block
- Include the AC ID in the test name: `'AC1 — Description of criterion'`

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `page.locator('.my-class')` CSS selectors | Use `getByTestId()` — class names change during refactors |
| Hardcoded test credentials in test files | Use environment variables and Keycloak test realm |
| Tests with no assertion | `test('it loads', async () => { await page.goto('/') })` is useless |
| `test.only()` or `test.skip()` in generated tests | Never bypass tests in generated code |

---

*Instructions — Phase 14 — AD Ports AI Portal — Applies to: Delivery Agents Squad*
