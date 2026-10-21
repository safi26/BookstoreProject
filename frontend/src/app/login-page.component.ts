import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService, USER_ROLES, UserRole } from './auth.service';

@Component({
  selector: 'app-login-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './login-page.component.html',
  styleUrls: []
})
export class LoginPageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  readonly userRoles = USER_ROLES;
  userRole: UserRole = 'Student';
  userId = '';
  password = '';
  showPassword = false;

  onSubmit(): void {
    const userId = this.userId.trim();
    if (!/^[1-9]\d*$/.test(userId) || !Number.isSafeInteger(Number(userId)) || !this.password) {
      return;
    }

    this.authService.startDemoSession(this.userRole, userId);
    void this.router.navigateByUrl('/store');
  }
}