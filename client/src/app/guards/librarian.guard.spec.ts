import { TestBed } from '@angular/core/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Router, UrlTree } from '@angular/router';
import { EMPTY, firstValueFrom, Observable, of } from 'rxjs';
import { configureTestBed } from '@testing';
import { AuthService } from '../services';
import { User } from '../models';
import { LibrarianGuard } from './librarian.guard';

describe('LibrarianGuard', () => {
  let isMatched: boolean;
  let loggedInUser$: Observable<User>;

  const build = (): LibrarianGuard => {
    configureTestBed();
    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: { getLoggedInUser: () => loggedInUser$ } },
        {
          provide: BreakpointObserver,
          useValue: {
            isMatched: () => isMatched,
            // MatSnackBar, pulled in by configureTestBed, observes this too.
            observe: () => of({ matches: isMatched, breakpoints: {} })
          }
        }
      ]
    });
    return TestBed.inject(LibrarianGuard);
  };

  beforeEach(() => {
    isMatched = false;
    loggedInUser$ = EMPTY;
  });

  it('sends signed-out mobile visitors home', async () => {
    isMatched = true;
    const result = await firstValueFrom(build().canActivate());

    expect(result instanceof UrlTree).toBe(true);
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/');
  });

  it('lets signed-out desktop visitors through to the sign-in prompt', async () => {
    isMatched = false;

    expect(await firstValueFrom(build().canActivate())).toBe(true);
  });

  it('lets signed-in mobile visitors through', async () => {
    isMatched = true;
    loggedInUser$ = of({ email: 'reader@papermast.test' } as User);

    expect(await firstValueFrom(build().canActivate())).toBe(true);
  });
});
