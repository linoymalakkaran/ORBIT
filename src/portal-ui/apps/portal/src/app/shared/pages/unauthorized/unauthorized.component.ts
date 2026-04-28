import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'orbit-unauthorized',
  standalone: true,
  imports: [RouterLink],
  template: `
    <div class="flex flex-col items-center justify-center h-64 text-center">
      <span class="pi pi-ban text-5xl text-red-400 mb-4"></span>
      <h2 class="text-2xl font-semibold mb-2">Access Denied</h2>
      <p class="text-surface-500 mb-6">You do not have permission to access this resource.</p>
      <a routerLink="/projects" class="text-primary-600 underline">Back to Projects</a>
    </div>
  `
})
export class UnauthorizedComponent {}
