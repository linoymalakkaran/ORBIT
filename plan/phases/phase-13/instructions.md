# Instructions — Phase 13: Frontend Specialist Agent

> Add this file to your IDE's custom instructions when building or extending the Frontend Specialist Agent.

---

## Context

You are building the **AD Ports Frontend Specialist Agent** — a Python-based AI agent that generates production-ready Angular 20 micro-frontend applications. The agent takes a `WorkPackage` from the Orchestrator and produces a complete Nx workspace with Native Federation configured, standalone components, PrimeNG UI, Tailwind CSS, Transloco i18n, and Keycloak auth — all wired together and ready to build.

---

## Angular Standards (Enforce — No Exceptions)

```typescript
// MANDATORY: Standalone components only
@Component({
  selector: 'adp-declaration-form',
  standalone: true,              // REQUIRED
  imports: [ReactiveFormsModule, InputTextModule, ButtonModule, TranslocoModule],
  templateUrl: './declaration-form.component.html',
})
export class DeclarationFormComponent {
  // inject() over constructor injection
  private readonly fb       = inject(FormBuilder);
  private readonly api      = inject(DeclarationApiService);  // Generated OpenAPI client
  private readonly router   = inject(Router);

  // Signals for state
  isLoading = signal(false);
  submitError = signal<string | null>(null);

  // Computed for derived state  
  canSubmit = computed(() => this.form.valid && !this.isLoading());

  form = this.fb.group({
    cargoType:   ['', [Validators.required]],
    weight:      [null as number | null, [Validators.required, Validators.min(0)]],
    originPort:  ['', [Validators.required, Validators.maxLength(50)]],
  });

  async submit(): Promise<void> {
    if (!this.canSubmit()) return;
    this.isLoading.set(true);
    this.submitError.set(null);
    try {
      await lastValueFrom(this.api.declarationsPost({ createDeclarationRequest: this.form.value }));
      this.router.navigate(['/declarations']);
    } catch (err) {
      this.submitError.set('declaration-form.submit-error');  // i18n key — never raw string
    } finally {
      this.isLoading.set(false);
    }
  }
}
```

## Template Rules

```html
<!-- CORRECT: PrimeNG components + Transloco for all text -->
<p-card [header]="'declaration-form.title' | transloco">
  <form [formGroup]="form" (ngSubmit)="submit()">
    <div class="flex flex-col gap-4">
      <!-- PrimeNG for controls, Tailwind for layout only -->
      <p-floatlabel>
        <input pInputText formControlName="cargoType" id="cargoType" />
        <label for="cargoType">{{ 'declaration-form.cargo-type' | transloco }}</label>
      </p-floatlabel>
    </div>

    <!-- Loading state with signal -->
    <p-button
      type="submit"
      [label]="'common.submit' | transloco"
      [loading]="isLoading()"
      [disabled]="!canSubmit()"
    />
  </form>
</p-card>

<!-- WRONG: Raw string in template -->
<button>Submit</button>  <!-- FORBIDDEN — use transloco -->
<input class="border p-2 rounded" />  <!-- FORBIDDEN — use PrimeNG pInputText -->
```

## i18n File Generation

Every generated component must seed translation files:

```json
// assets/i18n/en.json
{
  "declaration-form": {
    "title": "Submit Dangerous Goods Declaration",
    "cargo-type": "Cargo Type",
    "submit-error": "Failed to submit declaration. Please try again."
  }
}
```

```json
// assets/i18n/ar.json
{
  "declaration-form": {
    "title": "تقديم إعلان البضائع الخطرة",
    "cargo-type": "نوع البضاعة",
    "submit-error": "فشل في تقديم الإعلان. يرجى المحاولة مرة أخرى."
  }
}
```

## Keycloak Auth Guard Pattern

```typescript
// REQUIRED pattern for all protected routes
export const authGuard: CanActivateFn = (route, state) => {
  const keycloak = inject(KeycloakService);
  if (!keycloak.isLoggedIn()) {
    keycloak.login({ redirectUri: window.location.origin + state.url });
    return false;
  }
  return true;
};

// Route configuration
export const routes: Routes = [
  {
    path: 'declarations',
    canActivate: [authGuard],
    loadComponent: () => import('./features/declarations/declaration-list.component')
      .then(m => m.DeclarationListComponent),
  }
];
```

## OpenAPI Client Generation (Generated — Never Handwritten)

```typescript
// CORRECT: Use generated OpenAPI client
import { DeclarationsService } from '../api/declarations.service';  // Generated

// WRONG: Direct HttpClient
constructor(private http: HttpClient) {}
this.http.post('/api/declarations', body);  // FORBIDDEN
```

The Frontend Agent must generate the OpenAPI TypeScript client from the service's OpenAPI stub:

```python
# In frontend_agent/nodes/api_client_generation_node.py
async def generate_api_client(openapi_spec: str, output_dir: str) -> None:
    """Generate TypeScript client from OpenAPI spec using openapi-generator-cli."""
    await asyncio.create_subprocess_exec(
        "npx", "@openapitools/openapi-generator-cli", "generate",
        "-i", openapi_spec,
        "-g", "typescript-angular",
        "-o", f"{output_dir}/src/app/api",
        "--additional-properties", "ngVersion=20,modelPropertyNaming=camelCase",
    )
```

## Generated Output Structure

```
{project-name}-shell/              ← Nx workspace root
├── apps/
│   └── {project-name}-app/        ← Main Angular application
│       ├── src/
│       │   ├── app/
│       │   │   ├── app.config.ts   ← Standalone app config with Keycloak, Transloco
│       │   │   ├── app.routes.ts   ← Lazy-loaded routes
│       │   │   ├── api/            ← Generated OpenAPI TypeScript client
│       │   │   └── features/
│       │   │       └── {bounded-context}/
│       │   │           ├── {entity}-list/
│       │   │           ├── {entity}-form/
│       │   │           └── {entity}-detail/
│       │   └── assets/
│       │       └── i18n/
│       │           ├── en.json
│       │           └── ar.json
│       └── project.json
├── module-federation.config.ts     ← Native Federation config
├── nx.json
└── package.json
```

## Accessibility Requirements

All generated components must:
- Have `aria-label` or `aria-labelledby` on all interactive elements
- Support keyboard navigation
- Pass `ng lint` with `@angular-eslint/accessibility` rules enabled

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| `constructor` injection | Use `inject()` — required for Angular 20 standalone |
| `ngModel` / template-driven forms | Use `ReactiveFormsModule` only |
| Raw `HttpClient` calls | Use generated OpenAPI client only |
| String literals in templates | Use Transloco i18n keys |
| Non-PrimeNG input controls | Use PrimeNG — Tailwind is for layout only |
| `any` TypeScript type | Strict type checking is on — no `any` |

---

*Instructions — Phase 13 — AD Ports AI Portal — Applies to: Delivery Agents Squad*
