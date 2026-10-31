import { CommonModule } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

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
  userId = '';
  password = '';
  showPassword = false;
  submitting = false;
  loginError = '';

  onSubmit(): void {
    const userId = this.userId.trim();
    if (!/^[1-9]\d*$/.test(userId) || !Number.isSafeInteger(Number(userId)) || !this.password) {
      return;
    }

    this.submitting = true;
    this.loginError = '';
    this.authService.login(Number(userId), this.password).subscribe({
      next: () => {
        this.submitting = false;
        void this.router.navigateByUrl('/store');
      },
      error: error => {
        this.submitting = false;
        this.loginError = error instanceof HttpErrorResponse
          ? error.error?.detail ?? 'Could not log in. Check your user ID and password.'
          : 'Could not log in. Check your connection and try again.';
      }
    });
  }
}