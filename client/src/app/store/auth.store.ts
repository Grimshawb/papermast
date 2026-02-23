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
        if (res?.token) {
          localStorage.setItem('papermast_auth_token', res.token);
          this.setState({ logInResponse: 'Success! You Are Now Logged In' });
          this.getLoggedInUser();
        }
      });
  }

  public getLoggedInUser(): void {
    this._authService.getLoggedInUser()
      .pipe(take(1))
      .subscribe(u => this.setState({ loggedInUser: u }));
  }

  public initializeAuthState(): void {
    const token = this.getToken();
    if (token) this.getLoggedInUser();
  }

  public getToken(): any {
    return localStorage.getItem('papermast_auth_token');
  }

  public removeToken(): void {
    localStorage.removeItem('papermast_auth_token');
  }

  public setLoginResponse(res: any): void {
    this.setState({ logInResponse: res });
  }
}
