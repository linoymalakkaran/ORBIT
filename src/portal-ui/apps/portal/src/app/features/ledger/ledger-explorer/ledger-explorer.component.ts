import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { TagModule } from 'primeng/tag';
import { LedgerApiService } from '@orbit/api';

@Component({
  selector: 'orbit-ledger-explorer',
  standalone: true,
  imports: [CommonModule, FormsModule, TableModule, ButtonModule, InputTextModule, TagModule],
  template: `
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-2xl font-semibold">Ledger Explorer</h1>
      <div class="flex gap-2">
        <input pInputText [(ngModel)]="projectFilter" placeholder="Project ID" class="w-64" />
        <p-button label="Search" (onClick)="load()" icon="pi pi-search" />
        <p-button label="Verify Chain" (onClick)="verify()" severity="secondary"
          icon="pi pi-shield" [disabled]="!projectFilter" />
      </div>
    </div>

    <div *ngIf="chainResult()" class="mb-4 p-3 rounded-lg"
      [ngClass]="chainResult()!.valid ? 'bg-green-50 border border-green-300' : 'bg-red-50 border border-red-300'">
      <span class="font-medium">Chain: {{chainResult()!.valid ? '✓ Valid' : '✗ Tampered'}}</span>
      <span class="ml-2 text-sm text-surface-600">{{chainResult()!.checked}} entries checked</span>
      <span *ngIf="!chainResult()!.valid" class="ml-2 text-red-600 text-sm">
        Failed at: {{chainResult()!.failedAtEventId}}
      </span>
    </div>

    <p-table [value]="entries()" [loading]="loading()" [paginator]="true" [rows]="50">
      <ng-template pTemplate="header">
        <tr><th>Event Type</th><th>Stage</th><th>Occurred At</th><th>Entry Hash</th></tr>
      </ng-template>
      <ng-template pTemplate="body" let-e>
        <tr>
          <td><p-tag [value]="e.eventType" severity="info" /></td>
          <td>{{e.stageNumber ?? '—'}}</td>
          <td>{{e.occurredAt | date:'medium'}}</td>
          <td class="font-mono text-xs text-surface-500">{{e.entryHash?.slice(0,16)}}…</td>
        </tr>
      </ng-template>
    </p-table>
  `
})
export class LedgerExplorerComponent implements OnInit {
  private route  = inject(ActivatedRoute);
  private api    = inject(LedgerApiService);

  entries     = signal<any[]>([]);
  loading     = signal(false);
  chainResult = signal<any>(null);
  projectFilter = '';

  ngOnInit() {
    const pid = this.route.snapshot.queryParamMap.get('project');
    if (pid) { this.projectFilter = pid; this.load(); }
  }

  load() {
    if (!this.projectFilter) return;
    this.loading.set(true);
    this.api.byProject(this.projectFilter).subscribe({
      next: r => this.entries.set(r.items),
      complete: () => this.loading.set(false)
    });
  }

  verify() {
    this.api.verify(this.projectFilter).subscribe(r => this.chainResult.set(r));
  }
}
