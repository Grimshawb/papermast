import { Injectable } from "@angular/core";
import { CanActivate, Router, UrlTree } from "@angular/router";
import { AuthService } from "../services";
import { defaultIfEmpty, map, Observable } from "rxjs";

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(
    private _authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean | UrlTree> {
    return this._authService.getLoggedInUser()
      .pipe(
        // The global error interceptor completes unauthorized requests without
        // emitting, so default the empty stream to a logged-out result.
        defaultIfEmpty(null),
        map(user => user ? true : this.router.createUrlTree(['/login']))
      );
  }
}
