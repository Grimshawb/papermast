import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./application/home/home-page/home-page.component').then(m => m.HomePageComponent)

  },


  {
    path: '**',
    loadComponent: () => import('./navigation/bad-navigation/bad-navigation.component').then(m => m.BadNavigationComponent)
  }
];
