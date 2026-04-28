import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommonModule } from '@angular/common';
import { TabsModule } from 'primeng/tabs';
import { CardModule } from 'primeng/card';
import { TimelineModule } from 'primeng/timeline';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { ProjectsApiService, TeamApiService } from '@orbit/api';

@Component({
  selector: 'orbit-project-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, TabsModule, CardModule, TimelineModule, TagModule, ButtonModule],
  template: `
    <div *ngIf="project() as p">
      <div class="flex justify-between items-start mb-6">
        <div>
          <h1 class="text-2xl font-bold">{{p.displayName}}</h1>
          <p class="text-surface-500 mt-1">{{p.slug}} · {{p.program ?? 'No program'}}</p>
        </div>
        <p-tag [value]="p.status" [severity]="p.status === 'active' ? 'success' : 'secondary'" />
      </div>

      <p-tabs>
        <p-tab-panel header="Overview">
          <div class="grid grid-cols-3 gap-4 mt-4">
            <p-card header="Description">
              <p>{{p.description ?? 'No description provided.'}}</p>
            </p-card>
          </div>
        </p-tab-panel>

        <p-tab-panel header="Team ({{team().length}})">
          <div class="mt-4 space-y-2">
            @for (m of team(); track m.userId) {
              <div class="flex items-center gap-3 p-3 bg-surface-100 rounded-lg">
                <span class="font-medium">{{m.displayName ?? m.userId}}</span>
                <p-tag [value]="m.role" severity="info" />
              </div>
            }
          </div>
        </p-tab-panel>

        <p-tab-panel header="Artifacts">
          <a [routerLink]="['/projects', p.id, 'artifacts']" class="text-primary-600 underline">
            View artifacts →
          </a>
        </p-tab-panel>

        <p-tab-panel header="Ledger">
          <a [routerLink]="['/ledger']" [queryParams]="{project: p.id}" class="text-primary-600 underline">
            Open in Ledger Explorer →
          </a>
        </p-tab-panel>
      </p-tabs>
    </div>
  `
})
export class ProjectDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api   = inject(ProjectsApiService);
  private teamApi = inject(TeamApiService);

  project = signal<any>(null);
  team    = signal<any[]>([]);

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id')!;
    this.api.getById(id).subscribe(p => this.project.set(p));
    this.teamApi.list(id).subscribe(t => this.team.set(t));
  }
}
