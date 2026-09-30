import { Injectable } from '@angular/core';

export const USER_ROLES = ['Student', 'Manager', 'Operator'] as const;
export type UserRole = (typeof USER_ROLES)[number];

const SESSION_ROLE_KEY = 'commonplace-store-role';

@Injectable({ providedIn: 'root' })
export class AuthService {
  get currentRole(): UserRole | null {
    const role = sessionStorage.getItem(SESSION_ROLE_KEY);
    return USER_ROLES.includes(role as UserRole) ? role as UserRole : null;
  }

  get isAuthenticated(): boolean {
    return this.currentRole !== null;
  }

  startDemoSession(role: UserRole): void {
    sessionStorage.setItem(SESSION_ROLE_KEY, role);
  }

  signOut(): void {
    sessionStorage.removeItem(SESSION_ROLE_KEY);
  }
}
