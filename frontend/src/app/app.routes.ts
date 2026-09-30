import { Routes } from '@angular/router';
import { BookstoreDashboardComponent } from './bookstore-dashboard.component';
import { LandingPageComponent } from './landing-page.component';
import { LoginPageComponent } from './login-page.component';
import { storeAccessGuard } from './store-access.guard';

export const routes: Routes = [
	{ path: '', component: LandingPageComponent },
	{ path: 'login', component: LoginPageComponent },
	{ path: 'store', component: BookstoreDashboardComponent, canActivate: [storeAccessGuard] },
	{ path: '**', redirectTo: '' }
];
