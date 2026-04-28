import { Routes } from '@angular/router';
import { authGuard } from '@orbit/auth';

export const routes: Routes = [
  { path: '', redirectTo: '/projects', pathMatch: 'full' },
  {
    path: 'projects',
    canActivate: [authGuard],
    loadComponent: () => import('./features/projects/projects-list/projects-list.component')
      .then(m => m.ProjectsListComponent)
  },
  {
    path: 'projects/:id',
    canActivate: [authGuard],
    loadComponent: () => import('./features/projects/project-detail/project-detail.component')
      .then(m => m.ProjectDetailComponent)
  },
  {
    path: 'projects/:id/artifacts/:artifactId',
    canActivate: [authGuard],
    loadComponent: () => import('./features/artifacts/artifact-review/artifact-review.component')
      .then(m => m.ArtifactReviewComponent)
  },
  {
    path: 'ledger',
    canActivate: [authGuard],
    loadComponent: () => import('./features/ledger/ledger-explorer/ledger-explorer.component')
      .then(m => m.LedgerExplorerComponent)
  },
  {
    path: 'context/:projectId',
    canActivate: [authGuard],
    loadComponent: () => import('./features/context/context-thread/context-thread.component')
      .then(m => m.ContextThreadComponent)
  },
  {
    path: 'unauthorized',
    loadComponent: () => import('./shared/pages/unauthorized/unauthorized.component')
      .then(m => m.UnauthorizedComponent)
  },
  { path: '**', redirectTo: '/projects' }
];
