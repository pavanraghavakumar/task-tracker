import { computed, inject, Injectable, signal } from '@angular/core';
import { Router } from '@angular/router';
import { tap } from 'rxjs';
import { ApiService } from './api.service';
import { AuthData, User } from './models';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly tokenKey = 'taskflow_access_token';
  private readonly userKey = 'taskflow_user';
  private readonly currentUser = signal<User | null>(this.readUser());
  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => !!localStorage.getItem(this.tokenKey));
  login(payload: { email: string; password: string }) { return this.api.login(payload).pipe(tap(data => this.store(data))); }
  register(payload: { name: string; email: string; password: string }) { return this.api.register(payload).pipe(tap(data => this.store(data))); }
  token() { return localStorage.getItem(this.tokenKey); }
  logout() { localStorage.removeItem(this.tokenKey); localStorage.removeItem(this.userKey); this.currentUser.set(null); void this.router.navigate(['/login']); }
  private store(data: AuthData) { localStorage.setItem(this.tokenKey, data.access_token); localStorage.setItem(this.userKey, JSON.stringify(data.user)); this.currentUser.set(data.user); }
  private readUser(): User | null { try { const value = localStorage.getItem(this.userKey); return value ? JSON.parse(value) as User : null; } catch { return null; } }
}
