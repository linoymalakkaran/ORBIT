# Skill: Playwright E2E Baseline

## Skill ID
`playwright-e2e-baseline`

## Description
Generates a complete Playwright E2E test suite with Page Object Models from BRD acceptance criteria. Includes accessibility tests (Axe WCAG 2.1 AA) and multi-language tests (English + Arabic).

## When To Use
- Generating E2E tests for a new Angular MFE.
- Adding test coverage for a new feature from a BRD story.
- Running accessibility audits against an AD Ports portal page.

---

## Inputs Required

```json
{
  "mfeName": "string — the Angular MFE being tested",
  "baseUrl": "string — e.g. https://dev.portal.adports.ae/dgd",
  "acceptanceCriteria": [
    {
      "id": "AC-DGD-001",
      "title": "string",
      "role": "shipper | customs_officer | architect | pm | admin",
      "preconditions": ["string"],
      "steps": ["string"],
      "expectedResult": "string"
    }
  ],
  "accessibility": true,
  "rtlTesting": true
}
```

---

## Output Structure

```
e2e/
├── playwright.config.ts            — Multi-browser, baseURL config
├── fixtures/
│   └── auth.fixture.ts             — Keycloak test realm login helper
├── pages/                          — Page Object Models (one per feature page)
│   ├── login.page.ts
│   ├── declaration-form.page.ts
│   └── declaration-list.page.ts
├── tests/
│   ├── {feature}/{ac-id}.spec.ts   — One spec per acceptance criterion
│   └── accessibility/
│       └── {feature}-a11y.spec.ts
└── test-data/
    └── {feature}-fixtures.ts       — Typed test data factories
```

---

## Playwright Config Template

```typescript
export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  use: {
    baseURL: process.env.BASE_URL ?? 'https://dev.portal.adports.ae',
    trace: 'on-first-retry',
    video: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox',  use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit',   use: { ...devices['Desktop Safari'] } },
    { name: 'mobile',   use: { ...devices['iPhone 13'] } },
  ],
  reporter: [
    ['html', { open: 'never' }],
    ['junit', { outputFile: 'test-results/junit.xml' }]
  ],
});
```

---

## Test Pattern

```typescript
// tests/{feature}/{ac-id}.spec.ts
test.describe('AC-DGD-001: Shipper submits general cargo declaration', () => {
  test.use({ storageState: 'auth/shipper.json' });  // Pre-authenticated

  test('submits with required fields → gets reference number', async ({ page }) => {
    const form = new DeclarationFormPage(page);
    await form.navigate();
    await form.fillRequiredFields({ cargoType: 'GENERAL', weight: 500, ... });
    await form.submit();
    await expect(page.getByTestId('success-alert')).toContainText('DGD-');
  });
});
```

---

## Acceptance Criteria

- [ ] Tests generated for all BRD acceptance criteria.
- [ ] Axe accessibility test: zero violations at WCAG 2.1 AA level.
- [ ] RTL Arabic layout tested with `?lang=ar`.
- [ ] Multi-browser (Chromium + Firefox + WebKit) all pass.
- [ ] Mobile viewport test included.

---

## References

- [Phase 16 — QA Automation Agent](../../phases/phase-16/phase-16.md)
- [shared/instructions/security-baseline.md](../instructions/security-baseline.md)

---

*shared/skills/playwright-e2e-baseline.md — AI Portal — v1.0*
