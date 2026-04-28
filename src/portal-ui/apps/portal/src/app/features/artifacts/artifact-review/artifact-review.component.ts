import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { SplitterModule } from 'primeng/splitter';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { FormsModule } from '@angular/forms';
import { ArtifactsApiService, ApprovalsApiService } from '@orbit/api';

@Component({
  selector: 'orbit-artifact-review',
  standalone: true,
  imports: [CommonModule, SplitterModule, ButtonModule, TagModule, TextareaModule, FormsModule],
  template: `
    <div *ngIf="artifact() as a">
      <h2 class="text-xl font-semibold mb-4">Review: {{a.artifactType}} v{{a.version}}</h2>
      <p-splitter [panelSizes]="[60, 40]" styleClass="h-[70vh]">
        <ng-template pTemplate>
          <div class="p-4 overflow-auto h-full">
            <pre class="text-sm font-mono bg-surface-100 p-4 rounded">{{a.metadata | json}}</pre>
          </div>
        </ng-template>
        <ng-template pTemplate>
          <div class="p-4 flex flex-col gap-4">
            <h3 class="font-semibold">Decision</h3>
            <textarea pTextarea [(ngModel)]="comment" rows="5"
              placeholder="Leave a comment..." class="w-full"></textarea>
            <div class="flex gap-2">
              <p-button label="Approve"          severity="success" (onClick)="submit('approved')" />
              <p-button label="Request Changes"  severity="warn"    (onClick)="submit('changes-requested')" />
              <p-button label="Reject"           severity="danger"  (onClick)="submit('rejected')" />
            </div>
            <div class="mt-4">
              <h4 class="font-medium mb-2">Previous Approvals</h4>
              @for (ap of approvals(); track ap.id) {
                <div class="flex items-center gap-2 mb-1 text-sm">
                  <p-tag [value]="ap.decision"
                    [severity]="ap.decision === 'approved' ? 'success' : ap.decision === 'rejected' ? 'danger' : 'warn'" />
                  <span>{{ap.comment}}</span>
                </div>
              }
            </div>
          </div>
        </ng-template>
      </p-splitter>
    </div>
  `
})
export class ArtifactReviewComponent implements OnInit {
  private route    = inject(ActivatedRoute);
  private artApi   = inject(ArtifactsApiService);
  private apprvApi = inject(ApprovalsApiService);

  artifact  = signal<any>(null);
  approvals = signal<any[]>([]);
  comment   = '';

  ngOnInit() {
    const { id, artifactId } = this.route.snapshot.params;
    this.artApi.getById(id, artifactId).subscribe(a => this.artifact.set(a));
    this.apprvApi.list(artifactId).subscribe(ap => this.approvals.set(ap));
  }

  submit(decision: string) {
    const a = this.artifact();
    if (!a) return;
    this.apprvApi.submit(a.id, { decision, comment: this.comment, artifactHashesJson: `{"hash":"${a.contentHash}"}` })
      .subscribe(() => this.apprvApi.list(a.id).subscribe(ap => this.approvals.set(ap)));
  }
}
