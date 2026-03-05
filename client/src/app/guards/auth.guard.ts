import { Injectable } from "@angular/core";
import { CanActivate, Router } from "@angular/router";
import { AuthService } from "../services";
import { catchError, map, Observable, of } from "rxjs";

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(
    private _authService: AuthService,
    private router: Router
  ) {}

  canActivate(): Observable<boolean> {
    return this._authService.getLoggedInUser()
      .pipe(
        map(() => true),
        catchError(() => {
          this.router.navigate(['/login']);
          return of(false);
        })
      );
  }
}
