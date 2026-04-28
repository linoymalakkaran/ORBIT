# Skill: Angular Nx Microfrontend

## Skill ID
`angular-nx-microfrontend`

## Description
Scaffolds a production-ready Angular Micro-Frontend (MFE) using Nx, Native Federation, PrimeNG 18, Tailwind CSS, Transloco i18n, and Keycloak auth. Can create a new Nx workspace or add a new remote to an existing workspace.

## When To Use
- Creating a new Angular MFE for an AD Ports project.
- Adding a new remote to the JUL, PCS, or other existing Nx workspaces.
- Scaffolding Angular pages + components from BRD user journeys.

---

## Inputs Required

```json
{
  "mode": "new-workspace | add-remote",
  "mfeName": "string — kebab-case, e.g. dgd-mfe",
  "shellWorkspace": "string — only for add-remote mode, e.g. jul-shell",
  "features": [
    {
      "name": "string — kebab-case feature area, e.g. declarations",
      "userJourneys": [
        "Shipper submits declaration",
        "Officer reviews declaration"
      ],
      "openApiSpecPath": "string — path to OpenAPI YAML for this feature"
    }
  ],
  "i18n": {
    "defaultLang": "en",
    "supportedLangs": ["en", "ar"]
  },
  "auth": {
    "keycloakEnabled": true,
    "requiredRoles": ["shipper", "customs_officer"]
  }
}
```

---

## Output Structure

```
apps/{mfe-name}/
├── src/app/
│   ├── app.config.ts               — Keycloak + Transloco + PrimeNG bootstrap
│   ├── app.routes.ts               — Root routes with lazy loading
│   ├── {feature}/
│   │   ├── {feature}.routes.ts
│   │   ├── {feature}-list.component.ts
│   │   ├── {feature}-detail.component.ts
│   │   └── {feature}-form.component.ts  — Auto-generated from OpenAPI schema
│   └── shared/
│       ├── services/{feature}-api.service.ts
│       └── guards/auth.guard.ts
├── assets/i18n/en.json + ar.json   — All keys seeded from component list
├── module-federation.config.ts
├── Dockerfile
└── nginx.conf
```

---

## Key Patterns Generated

### App Config (app.config.ts)

```typescript
export const appConfig: ApplicationConfig = {
  providers: [
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideTransloco({ config: { availableLangs: ['en', 'ar'], defaultLang: 'en', reRenderOnLangChange: true } }),
    importProvidersFrom(KeycloakAngularModule),
    { provide: APP_INITIALIZER, useFactory: initializeKeycloak, deps: [KeycloakService], multi: true },
    providePrimeNG({ theme: { preset: Aura, options: { prefix: 'p', darkModeSelector: 'system' } } }),
  ],
};
```

### Form Generation

All `FormGroup` built from OpenAPI `requestBody` schema:
- Required fields → `Validators.required`.
- `minimum`/`maximum` → `Validators.min/max`.
- `pattern` → `Validators.pattern`.
- `enum` → `<p-dropdown [options]="...">`.
- `boolean` → `<p-checkbox>`.

### i18n

Translation keys generated for every component label, error message, and placeholder. Both `en.json` and `ar.json` seeded with all keys (Arabic values flagged as `TODO` for human translator).

---

## Acceptance Criteria

- [ ] `nx build {mfe-name} --configuration=production` passes.
- [ ] `nx test {mfe-name}` passes.
- [ ] MFE loads inside the shell via Native Federation without errors.
- [ ] Unauthenticated user redirected to Keycloak login.
- [ ] Language switcher toggles between English and Arabic.
- [ ] `dir="rtl"` applied to `<html>` when Arabic is selected.
- [ ] Docker image builds; deploys to dev AKS.

---

## References

- [shared/instructions/coding-standards-angular.md](../instructions/coding-standards-angular.md)
- [Phase 13 — Frontend Specialist Agent](../../phases/phase-13/phase-13.md)

---

*shared/skills/angular-nx-microfrontend.md — AI Portal — v1.0*
