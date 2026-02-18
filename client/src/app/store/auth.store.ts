import { Injectable } from '@angular/core';
import {  User } from '../models';
import { Store } from './store';
import { AuthService } from '../services/auth.service';
import { AuthStoreState } from '../models/state-models/auth-store-state.model';

@Injectable({
  providedIn: 'root'
})

export class AuthStore extends Store<AuthStoreState> {

  public constructor(private _authService: AuthService) {
    super({} as AuthStoreState);
  }


}
