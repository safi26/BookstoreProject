import { Injectable, inject } from '@angular/core';
import { Observable, tap } from 'rxjs';
import { ApiLoginResponse, StoreApiService } from './store-api.service';

export const USER_ROLES = ['Student', 'Manager'] as const;
export type UserRole = (typeof USER_ROLES)[number];

const SESSION_ROLE_KEY = 'commonplace-store-role';
const SESSION_USER_ID_KEY = 'commonplace-store-user-id';
const SESSION_TOKEN_KEY = 'commonplace-store-token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly storeApi = inject(StoreApiService);

  get currentRole(): UserRole | null {
    const role = sessionStorage.getItem(SESSION_ROLE_KEY);
    return role === 'Student' || role === 'Manager' ? role : null;
  }

  get isAuthenticated(): boolean {
    return this.currentRole !== null && Boolean(this.token);
  }

  get token(): string | null {
    return sessionStorage.getItem(SESSION_TOKEN_KEY);
  }

  get currentUserId(): number | null {
    const userId = sessionStorage.getItem(SESSION_USER_ID_KEY) ?? '';
    if (!/^\d+$/.test(userId)) {
      return null;
    }

    const numericUserId = Number(userId);
    return Number.isSafeInteger(numericUserId) && numericUserId > 0 ? numericUserId : null;
  }

  login(userId: number, password: string): Observable<ApiLoginResponse> {
    return this.storeApi.login(userId, password).pipe(
      tap(response => this.saveSession(response))
    );
  }

  signOut(): Observable<void> {
    return this.storeApi.logout().pipe(
      tap(() => this.clearSession())
    );
  }

  private saveSession(response: ApiLoginResponse): void {
    sessionStorage.setItem(SESSION_TOKEN_KEY, response.token);
    sessionStorage.setItem(SESSION_ROLE_KEY, response.role);
    sessionStorage.setItem(SESSION_USER_ID_KEY, String(response.user_id));
  }

  private clearSession(): void {
    sessionStorage.removeItem(SESSION_ROLE_KEY);
    sessionStorage.removeItem(SESSION_USER_ID_KEY);
    sessionStorage.removeItem(SESSION_TOKEN_KEY);
  }
}
