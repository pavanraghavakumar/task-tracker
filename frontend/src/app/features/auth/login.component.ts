import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth.service';

@Component({
  selector: 'app-login', standalone: true, imports: [ReactiveFormsModule, RouterLink], styleUrl: './auth-shared.scss', changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="auth-wrap">
      <section class="intro" aria-labelledby="welcome-title"><div><div class="brand">✦ TaskFlow</div><h1 id="welcome-title">Make every day count.</h1><p>Organize your priorities, keep deadlines visible, and turn progress into a daily habit.</p></div><div class="features"><div class="feature"><span>✓</span> Focused daily planning</div><div class="feature"><span>↗</span> Progress at a glance</div></div></section>
      <section class="panel" aria-labelledby="login-title"><h2 id="login-title">Welcome back</h2><p class="subtitle">Sign in to continue to your workspace.</p>
        @if (error()) { <div class="api-error" role="alert">{{ error() }}</div> }
        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
          <div class="field"><label for="email">Email address</label><input id="email" type="email" formControlName="email" autocomplete="email" placeholder="you@example.com" [attr.aria-invalid]="invalid('email')" />@if(invalid('email')){<p class="error">Enter a valid email address.</p>}</div>
          <div class="field"><label for="password">Password</label><input id="password" type="password" formControlName="password" autocomplete="current-password" placeholder="At least 8 characters" [attr.aria-invalid]="invalid('password')" />@if(invalid('password')){<p class="error">Password must contain at least 8 characters.</p>}</div>
          <button class="button primary submit" type="submit" [disabled]="loading()">{{ loading() ? 'Signing in…' : 'Sign in' }}</button>
        </form><p class="switch">New to TaskFlow? <a routerLink="/register">Create an account</a></p>
      </section>
    </main>`
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder); private readonly auth = inject(AuthService); private readonly router = inject(Router);
  readonly loading = signal(false); readonly error = signal('');
  readonly form = this.fb.nonNullable.group({ email: ['', [Validators.required, Validators.email]], password: ['', [Validators.required, Validators.minLength(8)]] });
  invalid(name: 'email'|'password') { const c=this.form.controls[name]; return c.invalid && (c.touched || c.dirty); }
  submit() { if(this.form.invalid){this.form.markAllAsTouched();return;} this.loading.set(true);this.error.set('');this.auth.login(this.form.getRawValue()).pipe(finalize(()=>this.loading.set(false))).subscribe({next:()=>void this.router.navigate(['/dashboard']),error:e=>this.error.set(e.error?.error?.message ?? 'Unable to sign in. Please try again.')}); }
}
