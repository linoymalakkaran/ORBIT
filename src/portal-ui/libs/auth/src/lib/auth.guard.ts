import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { KeycloakService } from 'keycloak-angular';

export const authGuard: CanActivateFn = async () => {
  const kc     = inject(KeycloakService);
  const router = inject(Router);

  const loggedIn = await kc.isLoggedIn();
  if (!loggedIn) { kc.login(); return false; }
  return true;
};
