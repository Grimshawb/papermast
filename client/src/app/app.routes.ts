import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./application/home/home-page/home-page.component').then(m => m.HomePageComponent)
  },
  {
    path: 'register',
    loadComponent: () => import('./application/authentication/registration-page/registration-page.component').then(m => m.RegistrationPageComponent)
  },
  {
    path: 'login',
    loadComponent: () => import('./application/authentication/login-page/login-page.component').then(m => m.LoginPageComponent)
  },
  {
    path: 'bestsellers',
    loadComponent: () => import('./application/bestsellers/bestsellers-page/bestsellers-page.component').then(m => m.BestsellersPageComponent)
  },
  {
    path: '**',
    loadComponent: () => import('./navigation/bad-navigation/bad-navigation.component').then(m => m.BadNavigationComponent)
  }
];
