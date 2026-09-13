import { Injectable } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { CanActivate, Router, UrlTree } from '@angular/router';
import { defaultIfEmpty, map, Observable } from 'rxjs';
import { AuthService } from '../services';
import { MOBILE_BREAKPOINT } from '../constants';

/**
 * On mobile the librarian page carries its own ask form, because there is no
 * header search box to fall back to. A signed-out phone visitor could therefore
 * submit a query that can only fail, so send them home instead. Desktop keeps
 * the page reachable — there the form lives in the header and the page shows a
 * sign-in prompt in its place.
 */
@Injectable({ providedIn: 'root' })
export class LibrarianGuard implements CanActivate {

  constructor(
    private auth: AuthService,
    private breakpointObserver: BreakpointObserver,
    private router: Router
  ) {}

  public canActivate(): Observable<boolean | UrlTree> {
    return this.auth.getLoggedInUser().pipe(
      // The global error interceptor completes unauthorized requests without
      // emitting, so default the empty stream to a logged-out result.
      defaultIfEmpty(null),
      map(user => {
        if (user) return true;
        return this.breakpointObserver.isMatched(MOBILE_BREAKPOINT)
          ? this.router.createUrlTree(['/'])
          : true;
      })
    );
  }
}
