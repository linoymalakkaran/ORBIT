# Phase 13 — Frontend Specialist Agent

## Summary

Implement the **Frontend Specialist Agent** — generates production-ready Angular micro-frontends (MFEs) using Nx, Native Federation, PrimeNG, Tailwind, Transloco, and Keycloak auth. The Frontend Agent either creates a new Nx workspace or adds a new MFE remote to an existing JUL/PCS workspace.

---

## Objectives

1. Implement Nx workspace scaffold generator (new project mode).
2. Implement MFE remote add generator (existing workspace mode).
3. Implement page/component generation from BRD user journeys and OpenAPI specs.
4. Implement Keycloak auth wiring (same patterns as Portal frontend).
5. Implement Transloco i18n scaffold (en + ar).
6. Implement Angular routing from component decomposition.
7. Implement PrimeNG form generation from OpenAPI request schemas.
8. Implement Dockerfile + Nginx config generation.
9. Implement Jest unit test scaffold + Playwright E2E skeleton.
10. Wire Frontend Agent to Orchestrator and Pipeline Ledger.

---

## Duration

**3 weeks** (runs in parallel with Phase 12)

**Squad:** Delivery Agents Squad (1 senior Angular engineer + 1 Python/AI)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Nx workspace generator | `nx affected --target=build` passes |
| D2 | MFE remote add | `dgd-mfe` added to existing JUL workspace; Module Federation config updated |
| D3 | Page/component generation | All BRD user journeys have corresponding page components |
| D4 | Keycloak auth wiring | Login redirects to Keycloak; auth guard protects routes |
| D5 | i18n scaffold | English + Arabic translation files; language switcher works |
| D6 | Angular routing | All routes defined; lazy loading; auth guards applied |
| D7 | PrimeNG form generation | Form generated from OpenAPI request body schema; validation works |
| D8 | Dockerfile + Nginx | Docker builds; Nginx serves SPA with correct `try_files` |
| D9 | Jest + Playwright skeleton | `nx test` passes; Playwright login flow runs |
| D10 | Ledger integration | Agent events in Pipeline Ledger |

---

## Generated MFE Structure

```
apps/{service-name}-mfe/
├── src/
│   ├── app/
│   │   ├── app.config.ts            ← Standalone app config with Keycloak
│   │   ├── app.routes.ts            ← Lazy-loaded feature routes
│   │   ├── layout/
│   │   │   └── shell.component.ts   ← Shared layout (sidebar, topbar)
│   │   ├── {feature}/               ← One folder per BRD feature area
│   │   │   ├── {feature}.routes.ts
│   │   │   ├── {feature}-list/
│   │   │   │   └── {feature}-list.component.ts
│   │   │   ├── {feature}-detail/
│   │   │   │   └── {feature}-detail.component.ts
│   │   │   └── {feature}-form/
│   │   │       └── {feature}-form.component.ts
│   │   └── shared/
│   │       ├── services/
│   │       │   └── {feature}-api.service.ts   ← Generated OpenAPI client usage
│   │       └── guards/
│   │           └── auth.guard.ts
│   ├── environments/
│   │   ├── environment.ts
│   │   └── environment.prod.ts
│   └── assets/
│       └── i18n/
│           ├── en.json
│           └── ar.json
│
├── module-federation.config.ts      ← Native Federation config
├── project.json                     ← Nx project config
├── Dockerfile
└── nginx.conf
```

---

## Form Generation from OpenAPI

Given the `CreateDeclarationRequest` OpenAPI schema:

```yaml
CreateDeclarationRequest:
  type: object
  required: [cargoType, weight, originPort, destinationPort]
  properties:
    cargoType:
      type: string
      enum: [GENERAL, DANGEROUS, PERISHABLE, OVERSIZED]
    weight:
      type: number
      minimum: 0.1
    originPort:
      type: string
      description: IATA/IATA port code
    destinationPort:
      type: string
    imoDangerousGoods:
      type: object
      properties:
        unNumber: { type: string, pattern: "^\\d{4}$" }
        hazardClass: { type: string }
```

The Frontend Agent generates:

```typescript
@Component({
  selector: 'adports-declaration-form',
  standalone: true,
  imports: [ReactiveFormsModule, DropdownModule, InputTextModule, InputNumberModule,
            ButtonModule, MessageModule, TranslocoModule],
  template: `
    <form [formGroup]="form" (ngSubmit)="submit()">
      <div class="field">
        <label for="cargoType">{{ 'declaration.cargoType' | transloco }} *</label>
        <p-dropdown id="cargoType" formControlName="cargoType"
          [options]="cargoTypeOptions" optionLabel="label" optionValue="value" />
        <small class="p-error" *ngIf="form.get('cargoType')?.invalid && submitted">
          {{ 'validation.required' | transloco }}
        </small>
      </div>
      <!-- ... more fields generated from schema ... -->
      <p-button type="submit" label="{{ 'common.submit' | transloco }}" [loading]="saving()" />
    </form>
  `
})
export class DeclarationFormComponent {
  readonly form = new FormGroup({
    cargoType: new FormControl<string>('', [Validators.required]),
    weight: new FormControl<number | null>(null, [Validators.required, Validators.min(0.1)]),
    originPort: new FormControl<string>('', [Validators.required]),
    destinationPort: new FormControl<string>('', [Validators.required]),
    imoDangerousGoods: new FormGroup({
      unNumber: new FormControl<string>('', [Validators.pattern(/^\d{4}$/)]),
      hazardClass: new FormControl<string>('')
    })
  });
}
```

---

## Native Federation Configuration

```typescript
// module-federation.config.ts — for a new MFE remote
export const config: ModuleFederationConfig = {
  name: 'dgd-mfe',
  exposes: {
    './Routes': './src/app/dgd/dgd.routes.ts'
  }
};

// shell app — add remote to existing workspace
// apps/jul-shell/module-federation.config.ts — UPDATED by agent
export const config: ModuleFederationConfig = {
  name: 'jul-shell',
  remotes: [
    'declarations-mfe',
    'pcs-mfe',
    'dgd-mfe'  // ← Added by agent
  ]
};
```

---

## Step-by-Step Execution Plan

### Week 1: Nx Scaffold + Routing + Auth

- [ ] Implement Nx workspace generator template.
- [ ] Implement MFE remote add generator (modifies existing workspace).
- [ ] Implement app.config.ts template (Keycloak auth, Transloco, PrimeNG themes).
- [ ] Implement routing generator from component decomposition.
- [ ] Implement auth guard + token interceptor templates.

### Week 2: Components + Forms + i18n

- [ ] Implement page component generator from BRD user journeys.
- [ ] Implement form generator from OpenAPI request schemas.
- [ ] Implement i18n scaffold (en.json + ar.json from component list).
- [ ] Implement shared service generator (wraps OpenAPI client).

### Week 3: Build Assets + Tests + Agent Wiring

- [ ] Implement Dockerfile + nginx.conf generator.
- [ ] Implement Jest unit test scaffold.
- [ ] Implement Playwright E2E skeleton (login flow + happy-path per user journey).
- [ ] Implement `FrontendAgentWorker` (receives work package, generates, pushes to GitLab).
- [ ] Wire to Orchestrator; integration test end-to-end.

---

## Gate Criterion

- Generated Angular MFE `dgd-mfe` builds successfully with `nx build dgd-mfe --configuration=production`.
- MFE integrates into existing JUL shell via Native Federation (shell loads remote at runtime).
- Generated form validates OpenAPI-required fields client-side.
- Keycloak auth works (unauthenticated user redirected to Keycloak; authenticated user lands on dashboard).
- `nx test dgd-mfe` passes; Playwright login flow runs.
- Docker image builds; deployed to dev AKS.

---

*Phase 13 — Frontend Specialist Agent — AI Portal — v1.0*
