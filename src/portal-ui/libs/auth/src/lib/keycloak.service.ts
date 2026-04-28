import { Injectable, inject } from '@angular/core';
import { KeycloakService } from 'keycloak-angular';

@Injectable({ providedIn: 'root' })
export class OrbitKeycloakService {
  private kc = inject(KeycloakService);

  get username(): string { return this.kc.getUsername(); }
  get token(): string | undefined { return this.kc.getKeycloakInstance().token; }

  hasRole(role: string): boolean { return this.kc.isUserInRole(role); }

  login()  { this.kc.login(); }
  logout() { this.kc.logout(); }

  async isLoggedIn(): Promise<boolean> { return this.kc.isLoggedIn(); }
}
