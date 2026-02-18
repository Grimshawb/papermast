import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./application/home/home-page/home-page.component').then(m => m.HomePageComponent)
  },
  {
    path: 'login',
    loadComponent: () => import('./application/authentication/login-page/login-page.component').then(m => m.LoginPageComponent)
  },
  {
    path: '**',
    loadComponent: () => import('./navigation/bad-navigation/bad-navigation.component').then(m => m.BadNavigationComponent)
  }
];
