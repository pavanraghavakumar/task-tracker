import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../core/auth.service';

function passwordsMatch(control: AbstractControl): ValidationErrors | null { return control.get('password')?.value === control.get('confirmPassword')?.value ? null : { mismatch: true }; }
@Component({
  selector:'app-register',standalone:true,imports:[ReactiveFormsModule,RouterLink],styleUrl:'./auth-shared.scss',changeDetection:ChangeDetectionStrategy.OnPush,
  template:`<main class="auth-wrap"><section class="intro" aria-labelledby="join-title"><div><div class="brand">✦ TaskFlow</div><h1 id="join-title">Your goals, beautifully organized.</h1><p>Create a calm, focused system for everything that matters.</p></div><div class="features"><div class="feature"><span>◎</span> One clear personal workspace</div><div class="feature"><span>✓</span> Free and entirely local</div></div></section>
  <section class="panel" aria-labelledby="register-title"><h2 id="register-title">Create your account</h2><p class="subtitle">Start organizing in less than a minute.</p>@if(error()){<div class="api-error" role="alert">{{error()}}</div>}
  <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
    <div class="field"><label for="name">Full name</label><input id="name" formControlName="name" autocomplete="name" placeholder="Alex Morgan" />@if(invalid('name')){<p class="error">Enter at least 2 characters.</p>}</div>
    <div class="field"><label for="email">Email address</label><input id="email" type="email" formControlName="email" autocomplete="email" placeholder="you@example.com" />@if(invalid('email')){<p class="error">Enter a valid email address.</p>}</div>
    <div class="field"><label for="password">Password</label><input id="password" type="password" formControlName="password" autocomplete="new-password" placeholder="At least 8 characters" />@if(invalid('password')){<p class="error">Use at least 8 characters, including a letter and number.</p>}</div>
    <div class="field"><label for="confirm">Confirm password</label><input id="confirm" type="password" formControlName="confirmPassword" autocomplete="new-password" />@if(form.hasError('mismatch')&&form.controls.confirmPassword.touched){<p class="error">Passwords do not match.</p>}</div>
    <button class="button primary submit" type="submit" [disabled]="loading()">{{loading()?'Creating account…':'Create account'}}</button>
  </form><p class="switch">Already have an account? <a routerLink="/login">Sign in</a></p></section></main>`
})
export class RegisterComponent {
  private readonly fb=inject(FormBuilder);private readonly auth=inject(AuthService);private readonly router=inject(Router);readonly loading=signal(false);readonly error=signal('');
  readonly form=this.fb.nonNullable.group({name:['',[Validators.required,Validators.minLength(2),Validators.maxLength(80)]],email:['',[Validators.required,Validators.email]],password:['',[Validators.required,Validators.minLength(8),Validators.pattern(/^(?=.*[A-Za-z])(?=.*\d).+$/)]],confirmPassword:['',Validators.required]},{validators:passwordsMatch});
  invalid(name:'name'|'email'|'password'){const c=this.form.controls[name];return c.invalid&&(c.touched||c.dirty)}
  submit(){if(this.form.invalid){this.form.markAllAsTouched();return;}const{name,email,password}=this.form.getRawValue();this.loading.set(true);this.error.set('');this.auth.register({name,email,password}).pipe(finalize(()=>this.loading.set(false))).subscribe({next:()=>void this.router.navigate(['/dashboard']),error:e=>this.error.set(e.error?.error?.message??'Unable to create your account.')});}
}
