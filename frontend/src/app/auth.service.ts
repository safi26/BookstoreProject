import { Injectable } from '@angular/core';

export const USER_ROLES = ['Student', 'Manager', 'Operator'] as const;
export type UserRole = (typeof USER_ROLES)[number];

const SESSION_ROLE_KEY = 'commonplace-store-role';
const SESSION_USER_ID_KEY = 'commonplace-store-user-id';

@Injectable({ providedIn: 'root' })
export class AuthService {
  get currentRole(): UserRole | null {
    const role = sessionStorage.getItem(SESSION_ROLE_KEY);
    return USER_ROLES.includes(role as UserRole) ? role as UserRole : null;
  }

  get isAuthenticated(): boolean {
    return this.currentRole !== null;
  }

  get currentUserId(): number | null {
    const userId = sessionStorage.getItem(SESSION_USER_ID_KEY) ?? '';
    if (!/^\d+$/.test(userId)) {
      return null;
    }

    const numericUserId = Number(userId);
    return Number.isSafeInteger(numericUserId) && numericUserId > 0 ? numericUserId : null;
  }

  startDemoSession(role: UserRole, userId: string): void {
    sessionStorage.setItem(SESSION_ROLE_KEY, role);
    sessionStorage.setItem(SESSION_USER_ID_KEY, userId);
  }

  signOut(): void {
    sessionStorage.removeItem(SESSION_ROLE_KEY);
    sessionStorage.removeItem(SESSION_USER_ID_KEY);
  }
}
