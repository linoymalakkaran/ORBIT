import { Component, inject } from '@angular/core';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { CommonModule } from '@angular/common';
import { ButtonModule } from 'primeng/button';
import { MenubarModule } from 'primeng/menubar';
import { MenuItem } from 'primeng/api';
import { KeycloakService } from 'keycloak-angular';

@Component({
  selector: 'orbit-nav-shell',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive, ButtonModule, MenubarModule],
  template: `
    <div class="flex flex-col min-h-screen">
      <header class="bg-surface-900 text-white shadow-md">
        <p-menubar [model]="navItems" styleClass="bg-transparent border-none">
          <ng-template pTemplate="start">
            <span class="text-xl font-bold text-primary-400 mr-6">ORBIT AI Portal</span>
          </ng-template>
          <ng-template pTemplate="end">
            <div class="flex items-center gap-3">
              <span class="text-sm text-surface-300">{{ username }}</span>
              <p-button label="Logout" severity="secondary" size="small"
                (onClick)="logout()" />
            </div>
          </ng-template>
        </p-menubar>
      </header>
      <main class="flex-1 p-6 bg-surface-50">
        <ng-content />
      </main>
    </div>
  `
})
export class NavShellComponent {
  private keycloak = inject(KeycloakService);

  username = this.keycloak.getUsername();

  navItems: MenuItem[] = [
    { label: 'Projects',     routerLink: '/projects',  icon: 'pi pi-folder' },
    { label: 'Ledger',       routerLink: '/ledger',    icon: 'pi pi-shield' },
  ];

  logout() { this.keycloak.logout(); }
}
