# AD Ports Angular Coding Standards

## Applies To

All Angular 20+ micro-frontends generated or maintained by the AI Portal. Applies to: Frontend Specialist Agent, Ticket Implementation Agent, PR Review Agent. Load this file as custom instructions in Copilot / Cursor for any Angular project.

---

## Required Versions

| Package | Version | Notes |
|---------|---------|-------|
| Angular | 20.x | Standalone components, signals |
| PrimeNG | 18.x | Primary UI component library |
| Tailwind CSS | 3.4.x | Utility classes for layout |
| Transloco | 7.x | i18n (en + ar) |
| Nx | 20.x | Monorepo + Native Federation |
| keycloak-js | 25.x | Auth |

---

## Component Rules

**All components must be standalone.** No `NgModule` unless required by a third-party library:

```typescript
@Component({
  selector: 'adports-declaration-form',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    DropdownModule,
    InputTextModule,
    ButtonModule,
    TranslocoModule,
  ],
  templateUrl: './declaration-form.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DeclarationFormComponent {
  // ALWAYS use inject() — NEVER constructor injection
  private readonly declarationService = inject(DeclarationApiService);
  private readonly transloco = inject(TranslocoService);

  // ALWAYS use signals for component state
  readonly declarations = signal<DeclarationDto[]>([]);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  // ALWAYS use computed() for derived state
  readonly hasDeclarations = computed(() => this.declarations().length > 0);
}
```

---

## Dependency Injection

```typescript
// CORRECT: inject() function
private readonly service = inject(DeclarationApiService);
private readonly router = inject(Router);

// WRONG: Constructor injection
// constructor(private service: DeclarationApiService) {}  ← DO NOT USE
```

---

## State Management

```typescript
// CORRECT: Signals for local/component state
readonly items = signal<DeclarationDto[]>([]);
readonly filter = signal<'all' | 'submitted' | 'approved'>('all');

// CORRECT: Computed for derived state
readonly filteredItems = computed(() =>
  this.filter() === 'all'
    ? this.items()
    : this.items().filter(i => i.status === this.filter())
);

// CORRECT: Update signal
this.items.set(response.data);
this.items.update(items => [...items, newItem]);

// WRONG: BehaviorSubject for local component state (use signals instead)
// private readonly _items$ = new BehaviorSubject<DeclarationDto[]>([]);

// RxJS + Observables are still acceptable for HTTP calls and global streams
// Use toSignal() to bridge observables to signals when needed
readonly declarations = toSignal(this.declarationService.getAll(), { initialValue: [] });
```

---

## HTTP & API Client

Use the generated OpenAPI client. Never write raw HttpClient calls:

```typescript
// CORRECT: Generated OpenAPI client
private readonly client = inject(DeclarationsClient);

async loadDeclarations() {
  this.loading.set(true);
  try {
    const response = await firstValueFrom(this.client.getDeclarations());
    this.declarations.set(response.items);
  } catch (err) {
    this.error.set(this.transloco.translate('errors.loadFailed'));
  } finally {
    this.loading.set(false);
  }
}

// WRONG: Direct HttpClient
// private readonly http = inject(HttpClient);
// this.http.get<DeclarationDto[]>('/api/declarations')...  ← DO NOT USE
```

---

## Routing

```typescript
// app.routes.ts — always lazy-load feature routes
export const routes: Routes = [
  {
    path: 'declarations',
    loadChildren: () => import('./declarations/declarations.routes').then(m => m.routes),
    canActivate: [authGuard],
  },
  {
    path: '',
    redirectTo: 'declarations',
    pathMatch: 'full',
  },
];

// Feature routes file
export const routes: Routes = [
  {
    path: '',
    component: DeclarationListComponent,
  },
  {
    path: 'new',
    component: DeclarationFormComponent,
    canActivate: [roleGuard(['shipper', 'customs_officer'])],
  },
  {
    path: ':id',
    component: DeclarationDetailComponent,
  },
];
```

---

## Forms

```typescript
// ALWAYS use ReactiveFormsModule — NEVER template-driven forms
readonly form = new FormGroup({
  cargoType: new FormControl<string>('', {
    validators: [Validators.required],
    nonNullable: true,  // ALWAYS use nonNullable for required fields
  }),
  weight: new FormControl<number | null>(null, [
    Validators.required,
    Validators.min(0.1),
    Validators.max(999999),
  ]),
});

// Form submission — ALWAYS check validity + handle loading state
async submit() {
  if (this.form.invalid) {
    this.form.markAllAsTouched();
    return;
  }
  this.saving.set(true);
  try {
    await this.submitDeclaration(this.form.getRawValue());
  } finally {
    this.saving.set(false);
  }
}
```

---

## i18n (Transloco)

```typescript
// ALWAYS use Transloco for all user-facing text
// NEVER use hardcoded English strings in templates

// Template
{{ 'declaration.cargoType' | transloco }}
{{ 'declaration.status.' + item.status | transloco }}

// Component
private readonly transloco = inject(TranslocoService);
const errorMsg = this.transloco.translate('errors.declarationSubmitFailed');

// Translation file structure: assets/i18n/en.json
{
  "declaration": {
    "cargoType": "Cargo Type",
    "status": {
      "draft": "Draft",
      "submitted": "Submitted",
      "approved": "Approved"
    }
  }
}

// Arabic: assets/i18n/ar.json (must exist for every key in en.json)
{
  "declaration": {
    "cargoType": "نوع البضاعة",
    "status": {
      "draft": "مسودة"
    }
  }
}
```

---

## PrimeNG Usage

```html
<!-- Use PrimeNG for all interactive controls -->
<p-dropdown
  formControlName="cargoType"
  [options]="cargoTypeOptions"
  optionLabel="label"
  optionValue="value"
  [placeholder]="'declaration.selectCargoType' | transloco"
/>

<p-button
  type="submit"
  [label]="'common.submit' | transloco"
  [loading]="saving()"
  severity="primary"
/>

<!-- Use Tailwind ONLY for layout, spacing, responsive design -->
<!-- NEVER use Tailwind to style PrimeNG component internals -->
<div class="grid grid-cols-2 gap-4 mt-4">
  <div class="field">
    <!-- PrimeNG input here -->
  </div>
</div>
```

---

## Keycloak Auth

```typescript
// auth.guard.ts — ALWAYS use the generated auth guard
export const authGuard: CanActivateFn = async () => {
  const keycloak = inject(KeycloakService);
  if (keycloak.isLoggedIn()) return true;
  await keycloak.login({ redirectUri: window.location.href });
  return false;
};

// roleGuard — check Keycloak realm roles
export const roleGuard = (requiredRoles: string[]): CanActivateFn =>
  () => {
    const keycloak = inject(KeycloakService);
    return requiredRoles.some(role => keycloak.isUserInRole(role));
  };

// In components — get current user
const keycloak = inject(KeycloakService);
const userId = keycloak.getKeycloakInstance().subject;
const roles = keycloak.getUserRoles();
```

---

## Testing Rules

```typescript
// Unit tests with jest + Angular Testing Library
// Test file: component-name.component.spec.ts

import { render, screen } from '@testing-library/angular';
import userEvent from '@testing-library/user-event';

describe('DeclarationFormComponent', () => {
  it('should show validation error when weight is negative', async () => {
    await render(DeclarationFormComponent, {
      providers: [
        { provide: DeclarationsClient, useValue: mockClient }
      ]
    });

    await userEvent.type(screen.getByLabelText(/weight/i), '-5');
    await userEvent.click(screen.getByRole('button', { name: /submit/i }));

    expect(screen.getByText(/weight must be/i)).toBeInTheDocument();
  });
});
```

---

## Native Federation (Module Federation)

```typescript
// module-federation.config.ts — remote app (MFE)
export const config: ModuleFederationConfig = {
  name: 'dgd-mfe',
  exposes: {
    './Routes': './src/app/dgd/dgd.routes.ts',
    // Only expose routes — NEVER expose internal components directly
  },
};

// Shell app — ALWAYS use loadRemoteModule with fallback
{
  path: 'dgd',
  loadChildren: () =>
    loadRemoteModule('dgd-mfe', './Routes').catch(() =>
      import('./fallback/mfe-unavailable.routes').then(m => m.routes)
    )
}
```

---

## Forbidden Patterns

- ❌ `NgModule` declarations (use standalone components)
- ❌ Constructor injection (use `inject()`)
- ❌ `BehaviorSubject` for local component state (use signals)
- ❌ Raw `HttpClient` calls (use generated OpenAPI client)
- ❌ Template-driven forms (`[(ngModel)]`)
- ❌ Hardcoded English strings in templates
- ❌ `any` type (use proper TypeScript types)
- ❌ `document.getElementById` or direct DOM manipulation
- ❌ Tailwind CSS to style PrimeNG component internals
- ❌ `console.log` in production code

---

*shared/instructions/coding-standards-angular.md — AI Portal — v1.0*
