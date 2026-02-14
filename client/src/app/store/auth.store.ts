import { Injectable } from '@angular/core';
import {  User } from '../models';
import { Store } from './store';
import { AuthService } from '../services/auth.service';

@Injectable({
  providedIn: 'root'
})

export class AuthStore extends Store<User> {

  public constructor(private _authService: AuthService) {
    super({} as User);
  }


}
