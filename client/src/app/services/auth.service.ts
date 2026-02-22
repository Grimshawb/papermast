import { Injectable } from '@angular/core';
import { environment } from '../../environment';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LoginRequestDto, RegistrationRequestDto, User } from '../models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private baseUrl = `${environment.BACK_END_URL}auth`;

  constructor(private http: HttpClient) {}

  register(request: RegistrationRequestDto): Observable<boolean> {
    return this.http.post<boolean>(`${this.baseUrl}/register`, request);
  }

  public login(request: LoginRequestDto): Observable<any> {
    return this.http.post<boolean>(`${this.baseUrl}/login`, request);
  }

  public getLoggedInUser(): Observable<User> {
    return this.http.get<User>(`${this.baseUrl}`);
  }
}
