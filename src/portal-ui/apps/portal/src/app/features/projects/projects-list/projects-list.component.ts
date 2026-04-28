import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TagModule } from 'primeng/tag';
import { DropdownModule } from 'primeng/dropdown';
import { ProjectsApiService } from '@orbit/api';

@Component({
  selector: 'orbit-projects-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, TableModule, ButtonModule,
    InputTextModule, TagModule, DropdownModule],
  template: `
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-2xl font-semibold">Projects</h1>
      <p-button label="New Project" icon="pi pi-plus" (onClick)="showCreate = true" />
    </div>

    <div class="flex gap-3 mb-4">
      <p-dropdown [options]="programs" [(ngModel)]="filterProgram" placeholder="All Programs"
        [showClear]="true" (onChange)="load()" />
      <p-dropdown [options]="statuses" [(ngModel)]="filterStatus" placeholder="All Statuses"
        [showClear]="true" (onChange)="load()" />
    </div>

    <p-table [value]="projects()" [loading]="loading()" [paginator]="true" [rows]="20"
      [lazy]="true" [totalRecords]="total()" (onLazyLoad)="onPage($event)"
      styleClass="p-datatable-striped">
      <ng-template pTemplate="header">
        <tr>
          <th>Name</th><th>Program</th><th>Status</th><th>Team</th><th>Created</th><th></th>
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-p>
        <tr>
          <td><a [routerLink]="['/projects', p.id]" class="text-primary-600 font-medium">{{p.displayName}}</a></td>
          <td>{{p.program ?? '—'}}</td>
          <td><p-tag [value]="p.status" [severity]="p.status === 'active' ? 'success' : 'secondary'" /></td>
          <td>{{p.teamSize}}</td>
          <td>{{p.createdAt | date:'mediumDate'}}</td>
          <td><p-button icon="pi pi-arrow-right" [routerLink]="['/projects', p.id]" severity="secondary" size="small" /></td>
        </tr>
      </ng-template>
    </p-table>
  `
})
export class ProjectsListComponent implements OnInit {
  private api = inject(ProjectsApiService);

  projects = signal<any[]>([]);
  loading  = signal(false);
  total    = signal(0);
  page = 1;
  filterProgram?: string;
  filterStatus?: string;
  showCreate = false;

  programs = ['JUL', 'PCS', 'Mirsal', 'Internal'].map(v => ({ label: v, value: v }));
  statuses = ['active', 'archived'].map(v => ({ label: v, value: v }));

  ngOnInit() { this.load(); }

  load() {
    this.loading.set(true);
    this.api.list(this.page, 20, this.filterProgram, this.filterStatus).subscribe({
      next: r => { this.projects.set(r.items); this.total.set(r.total); },
      complete: () => this.loading.set(false)
    });
  }

  onPage(e: any) { this.page = e.first / e.rows + 1; this.load(); }
}
