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
    if (!this.userId.trim() || !this.password) {
      return;
    }

    this.authService.startDemoSession(this.userRole, this.userId.trim());
    void this.router.navigateByUrl('/store');
  }
}