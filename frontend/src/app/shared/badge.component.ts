import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { Priority, TaskStatus } from '../core/models';

@Component({
  selector: 'app-badge', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="badge" [class]="'badge ' + value()">{{ label() }}</span>`,
  styles: [`
    .badge{display:inline-flex;align-items:center;border-radius:999px;padding:.3rem .65rem;font-size:.74rem;font-weight:800;line-height:1;white-space:nowrap;text-transform:capitalize}
    .low{color:#176b51;background:#dcf8ec}.medium{color:#9a5a06;background:#fff1c9}.high{color:#a93434;background:#ffe0e0}
    .pending{color:#7357b6;background:#eee8ff}.in_progress{color:#176999;background:#dff3ff}.completed{color:#176b51;background:#dcf8ec}
  `]
})
export class BadgeComponent {
  readonly value = input.required<Priority | TaskStatus>();
  label() { return this.value().replace('_', ' '); }
}
