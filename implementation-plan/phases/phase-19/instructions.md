# Instructions — Phase 19: Developer Portal & IDE Integration

> Add this file to your IDE's custom instructions when working on the Developer Portal or IDE integration features.

---

## Context

You are building the **AD Ports Developer Portal** — the self-service hub where development teams discover available AI capabilities, register their projects, view task history, configure IDE integrations, and monitor costs. The Developer Portal is an Angular 20 micro-frontend shell that aggregates multiple feature MFEs.

---

## Angular Shell Registration

```typescript
// apps/developer-portal-shell/module-federation.config.ts
import { withNativeFederation, shareAll } from '@angular-architects/native-federation';

export default withNativeFederation({
  name: 'developer-portal-shell',
  exposes: {},                       // Shell exposes nothing
  shared: {
    ...shareAll({ singleton: true, strictVersion: true, requiredVersion: 'auto' }),
  },
  remotes: {
    // Each feature is a lazy-loaded remote
    'project-registration': 'https://project-mfe.adports.ae/remoteEntry.json',
    'task-history':         'https://tasks-mfe.adports.ae/remoteEntry.json',
    'capability-browser':   'https://capabilities-mfe.adports.ae/remoteEntry.json',
    'cost-dashboard':       'https://costs-mfe.adports.ae/remoteEntry.json',
    'ide-config-generator': 'https://ide-config-mfe.adports.ae/remoteEntry.json',
  }
});
```

## IDE Configuration Generator

A key feature of the Developer Portal — generates ready-to-paste IDE config for all registered MCP servers:

```typescript
// Feature: ide-config-generator
@Component({
  selector: 'adp-ide-config-generator',
  standalone: true,
  imports: [SelectButtonModule, CodeHighlightModule, ClipboardModule, TranslocoModule],
  template: `
    <p-selectbutton [options]="ideOptions" [(ngModel)]="selectedIde" optionLabel="label" optionValue="value" />
    
    <pre class="bg-gray-900 text-green-400 p-4 rounded-lg mt-4">{{ generatedConfig() }}</pre>

    <p-button 
      [label]="'ide-config.copy' | transloco"
      (click)="copyToClipboard()"
      icon="pi pi-copy"
    />
  `,
})
export class IdeConfigGeneratorComponent {
  private readonly mcpApi = inject(McpCatalogService);
  private readonly clipboard = inject(Clipboard);

  selectedIde = signal<'copilot' | 'cursor' | 'claude'>('copilot');
  private servers = toSignal(this.mcpApi.getActiveServers());

  generatedConfig = computed(() => {
    const ide = this.selectedIde();
    const servers = this.servers() ?? [];
    return ide === 'copilot'
      ? generateCopilotConfig(servers)
      : ide === 'cursor'
        ? generateCursorConfig(servers)
        : generateClaudeDesktopConfig(servers);
  });

  copyToClipboard() {
    this.clipboard.copy(this.generatedConfig());
  }
}
```

## Project Registration Flow

```typescript
// Project registration must capture:
interface ProjectRegistrationForm {
  projectName:    string;          // Displayed in Portal
  serviceId:      string;          // snake_case, used as K8s label value
  domain:         string;          // e.g. "DGD", "LCS", "CRUISE"
  tier:           'pilot' | 'standard' | 'premium';
  gitlabRepoUrl:  string;          // Must match gitlab.adports.ae domain
  squadId:        string;          // Team owning the project
  architectId:    string;          // Architect responsible (Keycloak user ID)
}

// On registration: calls POST /api/projects
// Portal backend provisions:
//   - Keycloak project realm (via Keycloak MCP)
//   - OpenFGA project namespace
//   - Pipeline Ledger project stream
//   - ArgoCD Application manifests
//   - Initial budget allocation
```

## Capability Browser Requirements

The Capability Browser renders the Fabric content with:
- Full-text search across skills, specs, instructions
- Filter by: type, domain, agent, version
- Markdown rendering with syntax highlighting
- JSON Schema viewer with interactive validation
- "Load in IDE" button for each skill (copies instruction file path)

## Forbidden Patterns

| Pattern | Reason |
|---------|--------|
| Direct backend calls in shell app | All API calls go through the feature MFE services |
| Non-lazy routes | Shell must lazy-load all remotes |
| Showing error details to unauthenticated users | 401/403 shows generic message only |

---

*Instructions — Phase 19 — AD Ports AI Portal — Applies to: Portal UX Squad*
