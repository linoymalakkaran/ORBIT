# Phase 04 — Portal Frontend UI (Angular)

## Summary

Build the Angular-based Portal UI — the web surface where architects upload BRDs, approve architectures, monitor project health, browse the capability fabric, and view the Pipeline Ledger. The UI uses the same stack as AD Ports production applications (Angular 20, PrimeNG 18, Tailwind CSS, Nx monorepo, Native Federation, Keycloak auth).

---

## Objectives

1. Scaffold Nx monorepo with the Portal shell app and initial feature libs.
2. Implement Keycloak OIDC authentication with automatic token refresh.
3. Implement the Portal navigation shell with role-based visibility.
4. Build the Projects list and detail pages.
5. Build the Artifact review surface (side-by-side diff, rationale pane, approval buttons).
6. Build the Pipeline Ledger Explorer UI (queryable timeline view).
7. Build the shared project context thread view.
8. Build the Platform Health dashboard placeholder (filled in Phase 20).
9. Implement i18n with Transloco (English + Arabic).
10. Write unit tests (Jest) and E2E test skeletons (Playwright).

---

## Prerequisites

- Phase 03 complete (Portal Backend API deployed).
- Keycloak realm and client `portal-web` configured.
- API OpenAPI spec available at `/swagger/v1/swagger.json`.

---

## Duration

**3 weeks** (runs in parallel with Phase 03 week 3 and into Phase 05)

**Squad:** Core Squad (2 senior Angular engineers + 1 full-stack for shared work)

---

## Deliverables

| # | Deliverable | Acceptance Criterion |
|---|------------|---------------------|
| D1 | Nx monorepo scaffold | `nx affected --target=build` builds all apps and libs |
| D2 | Keycloak OIDC auth flow | Login/logout works; token refreshes silently; 401 redirects to login |
| D3 | Navigation shell with RBAC | Architects see different nav items than developers |
| D4 | Projects list + detail pages | List with filters; detail with timeline and team |
| D5 | Artifact review surface | Side-by-side diff; approval buttons fire API; comments work |
| D6 | Ledger Explorer | Query form; timeline list; event detail; chain hash verified |
| D7 | Shared context thread view | Shows turns chronologically; who said what; decisions highlighted |
| D8 | i18n (en + ar) | Language switcher works; all labels translated |
| D9 | Unit tests | ≥80% coverage on core components; `nx test` passes |
| D10 | E2E skeletons | Playwright project created; happy-path login flow passes |

---

## Nx Workspace Structure

```
apps/
├── portal/                    ← Shell application (routing, layout, auth)
│   ├── src/
│   │   ├── app/
│   │   │   ├── app.config.ts
│   │   │   ├── app.routes.ts
│   │   │   └── layout/
│   │   │       ├── shell.component.ts
│   │   │       ├── sidebar.component.ts
│   │   │       └── topbar.component.ts
│   │   └── environments/
│   └── project.json
│
libs/
├── auth/                      ← Keycloak auth lib (shared across all remotes)
│   ├── src/
│   │   ├── keycloak.service.ts
│   │   ├── auth.guard.ts
│   │   ├── token-interceptor.ts
│   │   └── auth.providers.ts
│   └── project.json
│
├── projects/                  ← Projects feature lib
│   ├── src/
│   │   ├── projects-list/
│   │   ├── project-detail/
│   │   └── project-create/
│   └── project.json
│
├── artifacts/                 ← Artifact review feature lib
│   ├── src/
│   │   ├── artifact-review/
│   │   ├── artifact-diff/
│   │   └── approval-panel/
│   └── project.json
│
├── ledger/                    ← Pipeline Ledger Explorer lib
│   ├── src/
│   │   ├── ledger-query/
│   │   ├── ledger-timeline/
│   │   └── ledger-event-detail/
│   └── project.json
│
├── context/                   ← Shared context thread lib
│   └── src/
│       ├── context-thread/
│       └── context-decision-card/
│
├── ui/                        ← Shared UI component library
│   └── src/
│       ├── status-badge/
│       ├── hash-display/
│       ├── timeline-entry/
│       └── diff-viewer/
│
└── api-client/                ← Generated OpenAPI client (ng-openapi-gen)
    └── src/
        └── lib/               ← Auto-generated from swagger.json
```

---

## Key Implementation Details

### Authentication (Keycloak)

Use `keycloak-js` directly (not a wrapper library) for full control:

```typescript
// libs/auth/src/keycloak.service.ts
@Injectable({ providedIn: 'root' })
export class KeycloakService {
  private readonly keycloak = new Keycloak({
    url: inject(KEYCLOAK_URL),
    realm: 'ai-portal',
    clientId: 'portal-web',
  });

  async init(): Promise<void> {
    await this.keycloak.init({
      onLoad: 'check-sso',
      silentCheckSsoRedirectUri: `${window.location.origin}/assets/silent-check-sso.html`,
      pkceMethod: 'S256',
    });
  }

  get userRoles(): string[] {
    return this.keycloak.realmAccess?.roles ?? [];
  }

  get userGroups(): string[] {
    const token = this.keycloak.tokenParsed as any;
    return token?.groups ?? [];
  }
}
```

### Role-Based Navigation

```typescript
// Navigation items are driven by group membership
const navItems = computed(() => [
  { label: 'Projects', icon: 'pi pi-folder', route: '/projects',
    visible: true },
  { label: 'Fleet Maintenance', icon: 'pi pi-refresh', route: '/fleet',
    visible: userGroups.includes('/platform-engineers') },
  { label: 'Admin', icon: 'pi pi-cog', route: '/admin',
    visible: userRoles.includes('portal:admin') },
]);
```

### Artifact Diff Viewer

The artifact diff viewer shows side-by-side changes between artifact versions:

```typescript
@Component({
  selector: 'adports-artifact-diff',
  template: `
    <div class="grid grid-cols-2 gap-4">
      <div class="border rounded p-4">
        <h3 class="text-sm font-mono text-gray-500">{{ leftVersion }}</h3>
        <pre class="text-xs" [innerHTML]="leftContent | diffHighlight:'removed'"></pre>
      </div>
      <div class="border rounded p-4">
        <h3 class="text-sm font-mono text-gray-500">{{ rightVersion }}</h3>
        <pre class="text-xs" [innerHTML]="rightContent | diffHighlight:'added'"></pre>
      </div>
    </div>
    <div class="mt-4 p-4 bg-blue-50 rounded">
      <h4 class="font-medium">Orchestrator Rationale</h4>
      <p class="text-sm">{{ rationale }}</p>
      <p class="text-xs text-gray-500 mt-2">Based on skills: {{ skillsUsed.join(', ') }}</p>
    </div>
  `
})
export class ArtifactDiffComponent { ... }
```

### Ledger Explorer

```typescript
@Component({
  selector: 'adports-ledger-timeline',
  template: `
    <div class="flex gap-4 mb-4">
      <p-dropdown [options]="projects" [(ngModel)]="selectedProject" placeholder="Filter by project" />
      <p-calendar [(ngModel)]="dateRange" selectionMode="range" />
      <p-multiSelect [options]="eventTypes" [(ngModel)]="selectedTypes" />
      <p-button label="Query" (onClick)="query()" />
    </div>
    <p-timeline [value]="events">
      <ng-template pTemplate="content" let-event>
        <adports-ledger-event-card [event]="event" />
      </ng-template>
    </p-timeline>
    <div class="chain-verify mt-4 p-2 rounded" [class.bg-green-50]="chainValid" [class.bg-red-50]="!chainValid">
      <span class="text-xs">Chain integrity: {{ chainValid ? '✓ Valid' : '✗ Tampered' }}</span>
    </div>
  `
})
export class LedgerTimelineComponent { ... }
```

---

## Styling Standards

- Use Tailwind CSS utility classes for layout and spacing.
- Use PrimeNG components for all interactive elements (dropdowns, tables, dialogs, timelines).
- Portal theme: AD Ports brand colours (`--adports-primary: #003366`, `--adports-accent: #E8A020`).
- Dark mode: optional but not Phase 03 scope — stub the toggle.
- RTL support via `dir="rtl"` toggle (required for Arabic i18n).
- Typography: Inter (body), JetBrains Mono (code/hashes).

---

## Step-by-Step Execution Plan

### Week 1: Shell + Auth + Navigation

- [ ] Scaffold Nx workspace with Angular 20.
- [ ] Set up Native Federation config.
- [ ] Implement Keycloak auth lib (login, logout, token refresh, silent SSO).
- [ ] Implement auth guard and token interceptor.
- [ ] Implement Portal shell layout (sidebar, topbar, content area).
- [ ] Implement role-based navigation.
- [ ] Set up Transloco with en/ar translation files.

### Week 2: Projects + Artifacts + Ledger

- [ ] Generate OpenAPI client from `/swagger/v1/swagger.json`.
- [ ] Implement Projects list page (table with filters, status badges).
- [ ] Implement Project detail page (timeline, team, settings tabs).
- [ ] Implement Artifact review surface (diff viewer + approval panel).
- [ ] Implement Ledger Explorer (query form + timeline + chain verify).
- [ ] Implement Shared context thread view.

### Week 3: Polish + Tests + Deploy

- [ ] Build i18n translations for all labels.
- [ ] Write unit tests for all smart components.
- [ ] Write Playwright E2E login flow.
- [ ] Configure Nginx container for SPA hosting (with sub-path rewrites).
- [ ] Write Dockerfile + Helm chart.
- [ ] Deploy to AKS `ai-portal-core` namespace.
- [ ] Verify Kong ingress serves the SPA at `https://portal.adports-ai.internal`.

---

## Gate Criterion

- All D1–D10 deliverables pass acceptance criteria.
- Login → project list → project detail → approve flow works end-to-end.
- Ledger Explorer shows real events from the running API.
- RTL mode (Arabic) renders without layout breaks.
- `nx build portal --configuration=production` produces a clean build.
- Deployed and accessible at Portal URL.

---

*Phase 04 — Portal Frontend UI — AI Portal — v1.0*
