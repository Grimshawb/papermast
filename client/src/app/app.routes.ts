import { Routes } from '@angular/router';
import { AuthGuard } from './guards/auth.guard';

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
    loadComponent: () => import('./application/bestsellers/bestsellers-page-two/bestsellers-page-two.component').then(m => m.BestsellersPageTwoComponent)
  },
  {
    path: 'genres',
    loadComponent: () => import('./application/genres/genre-directory/genre-directory.component').then(m => m.GenreDirectoryComponent)
  },
  {
    path: 'genres/:slug',
    loadComponent: () => import('./application/genres/genre-page/genre-page.component').then(m => m.GenrePageComponent)
  },
  {
    path: 'search',
    canActivate: [AuthGuard],
    loadComponent: () => import('./application/search/search-page.component').then(m => m.SearchPageComponent)
  },
  {
    path: 'shelves',
    canActivate: [AuthGuard],
    loadComponent: () => import('./application/shelves/shelves-page/shelves-page.component').then(m => m.ShelvesPageComponent)
  },
  {
    path: '**',
    loadComponent: () => import('./navigation/bad-navigation/bad-navigation.component').then(m => m.BadNavigationComponent)
  }
];
