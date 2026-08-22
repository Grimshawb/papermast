import { Injectable } from '@angular/core';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { defaultIfEmpty, map, Observable } from 'rxjs';
import { AuthService } from '../services';

@Injectable({ providedIn: 'root' })
export class AdminGuard implements CanActivate {
  constructor(private auth: AuthService, private router: Router) {}
  public canActivate(): Observable<boolean | UrlTree> {
    return this.auth.getLoggedInUser().pipe(
      defaultIfEmpty(null),
      map(user => user?.isAdmin ? true : this.router.createUrlTree(['/']))
    );
  }
}
