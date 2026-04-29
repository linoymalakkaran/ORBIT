---
owner: platform-team
version: "1.0"
next-review: "2026-10-01"
applies-to: ["frontend"]
---

# TypeScript / Angular Coding Standards

## TS001 — Naming Conventions

- Components / services / pipes: `PascalCase` classes, `kebab-case` selectors
- Variables and functions: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Interfaces prefixed with `I` for service contracts; plain names for models
- File naming: `feature-name.component.ts`, `feature-name.service.ts`

## TS002 — Strict TypeScript

- `"strict": true` in all `tsconfig.json` files — no exceptions
- No `any` type; use `unknown` + type guards if type is truly dynamic
- Prefer `readonly` on interface properties and class fields that do not change
- Use `as const` for literal-type constants
- Enable `noImplicitOverride` to enforce explicit `override` keyword

## TS003 — Angular Guidelines

- Use standalone components (`standalone: true`); no NgModules for new code
- Signals (`signal`, `computed`, `effect`) for reactive state — no raw BehaviorSubjects
- Use `inject()` function in constructor body or field-initialiser; avoid decorator injection
- All HTTP calls go through a typed service; components never call `HttpClient` directly
- Lazy-load all feature routes with `loadComponent` or `loadChildren`

## TS004 — Async / Observables

- Prefer `async`/`await` with `firstValueFrom` over subscribe-based code in services
- Unsubscribe with `takeUntilDestroyed()` (Angular 16+); never leave subscriptions open
- Use the `async` pipe in templates; avoid manual subscription in components
- Error handling: use `catchError` in service layer; propagate to UI via `ErrorService`

## TS005 — Code Quality

- Maximum component template size: 100 lines; extract sub-components when exceeded
- No business logic in components — delegate to services
- ESLint + `@angular-eslint` rules must pass with zero warnings
- All public service methods must have JSDoc comments
