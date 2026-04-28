# Phase 16 — QA Automation Agent

## Summary

Implement the **QA Automation Agent** — generates Playwright E2E test suites, k6 load test scripts, Axe accessibility audits, and Pact contract test stubs from BRD acceptance criteria and OpenAPI specifications. Every generated service gets test coverage on day one.

---

## Objectives

1. Implement Playwright E2E test generator from BRD acceptance criteria.
2. Implement k6 load test generator from performance targets in QA plan.
3. Implement Axe accessibility audit integration (WCAG 2.1 AA).
4. Implement Pact consumer contract test generator from OpenAPI specs.
5. Implement Pact provider verification scaffold.
6. Implement visual regression test scaffold (Playwright screenshots).
7. Implement test data factory generator.
8. Implement test pipeline stages (add to DevOps Agent outputs).
9. Wire QA Agent to Orchestrator delegation framework.
10. Integrate QA report with Portal UI (test results panel).

---

## Prerequisites

- Phase 12 (Backend Agent — generated services to test).
- Phase 13 (Frontend Agent — generated MFEs to test).
- Phase 15 (DevOps Agent — CI pipeline to add test stages to).
- Phase 03 (Portal Backend API — QA report upload endpoint).

---

## Duration

**3 weeks** (runs after Phase 13 is stable)

**Squad:** QA & Test Squad (2 senior QA engineers + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Playwright E2E suite | All BRD acceptance criteria covered; suite passes on DGD |
| D2 | k6 load test | 200 concurrent users at 95th percentile < 2s for DGD declaration |
| D3 | Axe accessibility | Zero WCAG 2.1 AA violations in DGD form |
| D4 | Pact consumer tests | Consumer contract for DGD MFE → declaration-service generated |
| D5 | Pact provider verification | Provider verification passes on CI |
| D6 | Visual regression | Baseline screenshots captured; diff threshold < 0.5% |
| D7 | Test data factory | Factory generates valid DGD test entities |
| D8 | CI integration | Test stages added to GitLab CI; test results in merge request |
| D9 | QA report upload | Results uploaded to Portal via QA report API |
| D10 | Ledger integration | Test run events (start/pass/fail) in Pipeline Ledger |

---

## Playwright E2E Generator

Given a BRD acceptance criterion:

```
AC-DGD-001: A logged-in shipper can submit a general cargo declaration with required fields filled.
Expected: System displays "Declaration submitted. Reference: DGD-XXXXXXXX" and status changes to "Submitted".
```

The QA Agent generates:

```typescript
// Generated: dgd-submission.spec.ts
import { test, expect } from '@playwright/test';
import { LoginPage } from '../pages/login.page';
import { DeclarationFormPage } from '../pages/declaration-form.page';

test.describe('AC-DGD-001: Shipper can submit general cargo declaration', () => {
  test.beforeEach(async ({ page }) => {
    const login = new LoginPage(page);
    await login.loginAsRole('shipper'); // Uses Keycloak test realm
  });

  test('submits declaration with required fields', async ({ page }) => {
    const form = new DeclarationFormPage(page);
    await form.navigate();

    // Fill required fields
    await form.selectCargoType('GENERAL');
    await form.fillWeight(500);
    await form.fillOriginPort('AEJEA');
    await form.fillDestinationPort('AEFJR');

    // Submit
    await form.submit();

    // Assert
    await expect(page.getByRole('alert')).toContainText('Declaration submitted');
    await expect(page.getByRole('alert')).toContainText('DGD-');
    await expect(page.getByTestId('declaration-status')).toContainText('Submitted');
  });

  test('shows validation error when required fields are missing', async ({ page }) => {
    const form = new DeclarationFormPage(page);
    await form.navigate();

    await form.submit(); // Submit empty form

    await expect(page.getByText('Cargo type is required')).toBeVisible();
    await expect(page.getByText('Weight is required')).toBeVisible();
  });
});
```

Page Object Model classes are also generated:

```typescript
// Generated: pages/declaration-form.page.ts
export class DeclarationFormPage {
  constructor(private page: Page) {}

  async navigate() {
    await this.page.goto('/dgd/declarations/new');
    await this.page.waitForLoadState('networkidle');
  }

  async selectCargoType(value: string) {
    await this.page.getByLabel('Cargo Type').click();
    await this.page.getByRole('option', { name: value }).click();
  }

  async fillWeight(value: number) {
    await this.page.getByLabel('Weight').fill(String(value));
  }

  async submit() {
    await this.page.getByRole('button', { name: 'Submit' }).click();
  }
}
```

---

## k6 Load Test Generator

```javascript
// Generated: k6/dgd-load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const declarationSubmitTime = new Trend('declaration_submit_time');

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up
    { duration: '5m', target: 200 },  // Sustained load (200 concurrent users)
    { duration: '2m', target: 0 },    // Ramp down
  ],
  thresholds: {
    'declaration_submit_time': ['p(95)<2000'],  // 95th percentile < 2s
    'errors': ['rate<0.01'],                    // Error rate < 1%
  },
};

export default function() {
  const token = getAuthToken();  // Reusable token from k6 setup

  const payload = JSON.stringify({
    cargoType: 'GENERAL',
    weight: randomWeight(),
    originPort: 'AEJEA',
    destinationPort: 'AEFJR'
  });

  const response = http.post(
    `${__ENV.BASE_URL}/dgd/api/declarations`,
    payload,
    { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` } }
  );

  const startTime = Date.now();
  check(response, {
    'status is 201': (r) => r.status === 201,
    'has reference number': (r) => JSON.parse(r.body).referenceNumber?.startsWith('DGD-'),
  });

  errorRate.add(response.status !== 201);
  declarationSubmitTime.add(Date.now() - startTime);

  sleep(1);
}
```

---

## Axe Accessibility Integration

```typescript
// Generated: accessibility/dgd-a11y.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('WCAG 2.1 AA — DGD Declaration Form', () => {
  test('declaration form has no accessibility violations', async ({ page }) => {
    await page.goto('/dgd/declarations/new');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();

    expect(results.violations).toHaveLength(0);
  });

  test('RTL Arabic layout has no accessibility violations', async ({ page }) => {
    await page.goto('/dgd/declarations/new?lang=ar');

    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();

    expect(results.violations).toHaveLength(0);
  });
});
```

---

## Pact Contract Test Generator

```typescript
// Generated: contracts/dgd-mfe-declaration-service.pact.spec.ts
import { PactV3, MatchersV3 } from '@pact-foundation/pact';

const provider = new PactV3({
  consumer: 'dgd-mfe',
  provider: 'declaration-service',
  dir: './pacts',
});

describe('DGD MFE <-> Declaration Service', () => {
  it('fetches a declaration by ID', () => {
    return provider.addInteraction({
      states: [{ description: 'declaration DGD-00001 exists' }],
      uponReceiving: 'GET /declarations/DGD-00001',
      withRequest: {
        method: 'GET',
        path: '/api/declarations/DGD-00001',
        headers: { Authorization: MatchersV3.regex(/Bearer .+/, 'Bearer test-token') }
      },
      willRespondWith: {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
        body: {
          referenceNumber: MatchersV3.string('DGD-00001'),
          cargoType: MatchersV3.string('GENERAL'),
          status: MatchersV3.string('Submitted'),
        }
      }
    })
    .executeTest(async (mockServer) => {
      const client = new DeclarationApiClient(mockServer.url);
      const declaration = await client.getById('DGD-00001');
      expect(declaration.referenceNumber).toBe('DGD-00001');
    });
  });
});
```

---

## Step-by-Step Execution Plan

### Week 1: Playwright + Axe

- [ ] Implement BRD acceptance criteria parser (extracts test scenarios).
- [ ] Implement Playwright test generator (spec files + Page Object Models).
- [ ] Implement Axe accessibility test generator.
- [ ] Implement Playwright config generator (multi-browser, mobile viewports).

### Week 2: k6 + Pact

- [ ] Implement k6 load test generator from performance targets.
- [ ] Implement Pact consumer contract generator from OpenAPI schemas.
- [ ] Implement Pact provider verification scaffold.
- [ ] Implement test data factory generator.

### Week 3: CI Integration + Agent Wiring

- [ ] Implement CI stage additions (Playwright + k6 + Pact stages for DevOps Agent).
- [ ] Implement QA report upload to Portal API.
- [ ] Implement `QAAgentWorker` in Orchestrator framework.
- [ ] End-to-end test: DGD project → QA Agent generates all test types → all pass in CI.

---

## Gate Criterion

- All BRD acceptance criteria for DGD have corresponding Playwright tests.
- `npx playwright test` passes (all browsers: Chromium, Firefox, WebKit).
- k6 load test passes 200 concurrent users at p95 < 2s.
- Axe scan reports zero WCAG 2.1 AA violations.
- Pact consumer/provider contract tests pass.
- QA report uploaded to Portal and visible in project dashboard.

---

*Phase 16 — QA Automation Agent — AI Portal — v1.0*
