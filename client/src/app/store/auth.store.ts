import { Injectable } from '@angular/core';
import {  LoginRequestDto, User } from '../models';
import { Store } from './store';
import { AuthService } from '../services/auth.service';
import { AuthStoreState } from '../models/state-models/auth-store-state.model';
import { take, tap } from 'rxjs';

@Injectable({
  providedIn: 'root'
})

export class AuthStore extends Store<AuthStoreState> {

  public constructor(private _authService: AuthService) {
    super({} as AuthStoreState);
  }

  public login(loginRequest: LoginRequestDto): void {
    this._authService.login(loginRequest)
      .pipe(take(1))
      .subscribe(res => {
        this.setState({ logInResponse: 'Success! You Are Now Logged In' });
        this.getLoggedInUser();
      });
  }

  public initializeAuthState(): void {
    this.getLoggedInUser();
  }

  public getLoggedInUser(): void {
    this._authService.getLoggedInUser()
      .pipe(take(1))
      .subscribe(u => this.setState({ loggedInUser: u }));
  }

  public logout(): void {
    this._authService.logout()
      .pipe(take(1))
      .subscribe(() => {
        this.setState({ loggedInUser: null });
      });
  }
}
