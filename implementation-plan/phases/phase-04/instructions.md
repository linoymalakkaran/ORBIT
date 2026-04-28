# Instructions — Phase 04: Portal Frontend UI (Angular)

> Add this file to your IDE's custom instructions when building Portal Angular code.

---

## Context

You are building the **AD Ports AI Portal frontend** — an Angular 20 application using Nx monorepo, PrimeNG 18, Tailwind CSS, Transloco i18n, and `keycloak-js` for authentication. The application follows the same stack as AD Ports' JUL and PCS frontends.

---

## Angular Coding Standards

### Component Style

- All new components use `standalone: true` — no `NgModule`.
- Use Angular signals for reactive state: `signal()`, `computed()`, `effect()`.
- Use `inject()` function instead of constructor injection.
- Strongly-typed template variables — avoid `any`.
- Components are in `PascalCase`, files in `kebab-case`.

```typescript
// CORRECT — standalone component with signals
@Component({
  selector: 'adports-project-list',
  standalone: true,
  imports: [CommonModule, TableModule, ButtonModule, RouterModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `...`
})
export class ProjectListComponent {
  private readonly projectsService = inject(ProjectsService);
  readonly projects = this.projectsService.projects;
  readonly loading = this.projectsService.loading;
}
```

### State Management

- Use Angular signals for component-local state.
- Use service-level `signal()` for shared state across a feature.
- Do NOT use NgRx — overkill for the Portal (keep it simple).
- Services are `providedIn: 'root'` unless they need feature scoping.

### HTTP Client

- Use `HttpClient` with typed generics.
- Use the generated OpenAPI client from `libs/api-client` — never write raw HTTP calls.
- Handle errors with a global HTTP interceptor that translates 4xx/5xx to user-facing messages.
- All API calls include the Keycloak Bearer token via the token interceptor.

```typescript
// CORRECT — use generated client
export class ProjectsService {
  private readonly api = inject(ProjectsApiService); // generated from OpenAPI

  readonly projects = signal<ProjectDto[]>([]);

  async loadProjects(): Promise<void> {
    const result = await firstValueFrom(this.api.listProjects());
    this.projects.set(result.items);
  }
}
```

### Routing

- All routes are lazy-loaded.
- Route guards use the functional `CanActivateFn` pattern.
- Router uses `withComponentInputBinding()` to bind route params to component inputs.

```typescript
// CORRECT — lazy route
{
  path: 'projects',
  loadComponent: () =>
    import('./projects-list/projects-list.component').then(m => m.ProjectsListComponent),
  canActivate: [authGuard]
}
```

### Template Rules

- All user-visible strings must go through Transloco: `{{ 'projects.title' | transloco }}`.
- No inline styles — use Tailwind classes or PrimeNG theme variables.
- Use PrimeNG `p-*` components for all interactive elements.
- Use Angular `trackBy` (or the new `track` syntax) on all `@for` loops.
- Use `ChangeDetectionStrategy.OnPush` on all components.

---

## PrimeNG Usage

```typescript
// Use PrimeNG table with lazy loading for large datasets
<p-table
  [value]="projects()"
  [loading]="loading()"
  [paginator]="true"
  [rows]="20"
  [lazy]="true"
  (onLazyLoad)="loadLazy($event)"
  styleClass="p-datatable-sm"
>
```

PrimeNG components to use by area:
- **Tables/lists:** `p-table`, `p-dataView`
- **Forms:** `p-inputText`, `p-dropdown`, `p-calendar`, `p-multiSelect`
- **Dialogs:** `p-dialog`, `p-confirmDialog`
- **Navigation:** `p-panelMenu`, `p-tabView`, `p-breadcrumb`
- **Status:** `p-tag`, `p-badge`, `p-timeline`
- **Actions:** `p-button`, `p-splitButton`, `p-menu`
- **Notifications:** `p-toast` (global), `p-message` (inline)

---

## i18n with Transloco

```typescript
// Translation keys follow dot-notation hierarchy
// en.json
{
  "projects": {
    "title": "Projects",
    "createNew": "New Project",
    "status": {
      "active": "Active",
      "archived": "Archived",
      "pending": "Pending Review"
    }
  }
}

// Component usage
{{ 'projects.title' | transloco }}
{{ 'projects.status.' + project.status | transloco }}
```

- Translation files live in `apps/portal/src/assets/i18n/{lang}.json`.
- Never use hardcoded English strings in templates.
- RTL direction toggled by setting `document.documentElement.dir = 'rtl'` on language switch.

---

## Testing

```typescript
// Unit test — use TestBed with standalone component
describe('ProjectListComponent', () => {
  let component: ProjectListComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ProjectListComponent],
      providers: [
        { provide: ProjectsApiService, useValue: mockProjectsApi }
      ]
    }).compileComponents();
  });

  it('should display projects after loading', async () => {
    mockProjectsApi.listProjects.mockReturnValue(of({ items: [testProject] }));
    component.loadProjects();
    expect(component.projects()).toHaveLength(1);
  });
});
```

- Unit tests use `jest` with Angular Testing Library.
- E2E tests use `Playwright` — see `shared/skills/playwright-e2e-baseline.md`.
- All component tests mock services — no real HTTP calls in unit tests.

---

## What NOT to Do

- Do not use `NgModule` for new code — standalone components only.
- Do not use `@HostListener` — prefer event bindings in templates.
- Do not use `ElementRef` for DOM manipulation — use Angular directives.
- Do not use `document.getElementById` or any direct DOM access.
- Do not import PrimeNG modules in the root `AppComponent` — import in each feature component.
- Do not use `any` type in component code.
- Do not put business logic in components — put it in services.
- Do not call the API directly from a component — always use a service.

---

*Phase 04 Instructions — AI Portal — v1.0*
