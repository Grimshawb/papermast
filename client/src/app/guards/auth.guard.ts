import { Injectable } from "@angular/core";
import { CanActivate, Router } from "@angular/router";
import { AuthStore } from "../store/auth.store";

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate {

  constructor(private _authStore: AuthStore,
              private router: Router) {}

  canActivate(): boolean {

    if (this._authStore.getToken()) {
      return true;
    }

    this.router.navigate(['/login']);
    return false;
  }
}
