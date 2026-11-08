import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-loading', standalone: true, changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<div class="loading" role="status"><span class="spinner" aria-hidden="true"></span><span>{{ label() }}</span></div>`,
  styles: [`.loading{display:flex;align-items:center;justify-content:center;gap:.75rem;padding:3rem;color:var(--muted)}.spinner{width:1.35rem;height:1.35rem;border:3px solid #dfe3f1;border-top-color:var(--primary);border-radius:50%;animation:spin .7s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}`]
})
export class LoadingComponent { readonly label = input('Loading…'); }
