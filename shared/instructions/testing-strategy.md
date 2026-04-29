---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["backend", "frontend", "devops"]
---

# Testing Strategy

## Test Pyramid

```
         ┌─────────────┐
         │  E2E (5%)   │  Playwright (UI), Newman (API)
         ├─────────────┤
         │Integration  │  TestContainers, WireMock, Pact
         │   (25%)     │
         ├─────────────┤
         │  Unit (70%) │  xUnit (.NET), pytest (Python), Jest (Angular)
         └─────────────┘
```

## Unit Tests

- Coverage target: **≥ 80%** lines; **≥ 70%** branches; enforced in CI (SonarQube gate)
- Test naming: `MethodName_StateUnderTest_ExpectedBehavior`
- One assertion focus per test; use `FluentAssertions` (.NET) / `pytest-assertj` (Python)
- No test should touch the database, filesystem, or network — use `Moq`/`unittest.mock`
- All tests must run < 1s each; > 1s tests are moved to integration suite

## Integration Tests

- Use `TestContainers` for real PostgreSQL/Redis containers in integration tests
- Isolate test data: each test creates and cleans up its own data
- Use `WireMock` for external HTTP dependencies
- Contract tests with **Pact** for all consumer → provider pairs
- Integration test suite runs in `test:integration` CI job (separate from unit tests)

## End-to-End Tests

- **Playwright** for UI workflows; tests live in `e2e/` at project root
- **Newman** (Postman) for API smoke tests in staging after deployment
- E2E tests run in `test:e2e` CI job on staging environment only
- Critical paths tested: project creation, AI generation request, approval workflow, artifact download

## Performance Tests

- **k6** load scripts in `tests/performance/`
- P95 latency target: < 2s for AI generation initiation; < 200ms for read endpoints
- Throughput target: 100 concurrent users minimum
- Run in `test:perf` CI job on staging; results published to Grafana dashboard

## Test Data

- No production data in tests; use factories (`Bogus` for .NET, `Faker` for Python)
- Seed data scripts in `tests/fixtures/`; applied by `scripts/seed-test-data.sh`
- PCI-DSS test environments must not contain real card numbers — use Luhn-valid fake PANs

## Accessibility (A11y)

- Run **axe-core** audit on all Angular pages in Playwright tests
- Must achieve WCAG 2.1 AA compliance — zero critical/serious axe violations

## Code Quality Gates (SonarQube)

| Metric | Threshold |
|---|---|
| Coverage | ≥ 80% |
| Duplicated Lines | ≤ 3% |
| Maintainability Rating | A |
| Reliability Rating | A |
| Security Rating | A |
| Security Hotspots Reviewed | 100% |
