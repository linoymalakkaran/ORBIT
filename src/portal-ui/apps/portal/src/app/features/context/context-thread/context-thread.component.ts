import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { ScrollPanelModule } from 'primeng/scrollpanel';
import { ContextApiService } from '@orbit/api';

@Component({
  selector: 'orbit-context-thread',
  standalone: true,
  imports: [CommonModule, FormsModule, ButtonModule, InputTextModule, ScrollPanelModule],
  template: `
    <div class="flex flex-col h-[80vh]">
      <h2 class="text-xl font-semibold mb-3">Context Thread</h2>
      <p-scrollPanel styleClass="flex-1 mb-4">
        <div class="space-y-3 p-3">
          @for (msg of messages(); track msg.id) {
            <div class="p-3 rounded-lg"
              [ngClass]="msg.role === 'user' ? 'bg-primary-50 ml-12' : 'bg-surface-100 mr-12'">
              <span class="text-xs text-surface-500 font-medium uppercase">{{msg.role}}</span>
              <p class="mt-1 text-sm whitespace-pre-wrap">{{msg.content}}</p>
            </div>
          }
        </div>
      </p-scrollPanel>
      <div class="flex gap-2">
        <input pInputText [(ngModel)]="draft" class="flex-1" placeholder="Type a message…"
          (keydown.enter)="send()" />
        <p-button label="Send" (onClick)="send()" icon="pi pi-send" />
      </div>
    </div>
  `
})
export class ContextThreadComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private api   = inject(ContextApiService);

  messages = signal<any[]>([]);
  draft    = '';
  projectId = '';

  ngOnInit() {
    this.projectId = this.route.snapshot.paramMap.get('projectId')!;
    this.api.getThread(this.projectId).subscribe(r => this.messages.set(r));
  }

  send() {
    if (!this.draft.trim()) return;
    const msg = this.draft.trim();
    this.draft = '';
    this.api.append(this.projectId, msg).subscribe(r => this.messages.set(r));
  }
}
