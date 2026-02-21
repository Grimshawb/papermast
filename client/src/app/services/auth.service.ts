import { Injectable } from '@angular/core';
import { environment } from '../../environment';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { RegistrationRequestDto } from '../models';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  private baseUrl = `${environment.BACK_END_URL}auth`;

  constructor(private http: HttpClient) {}

  register(request: RegistrationRequestDto): Observable<boolean> {
    return this.http.post<boolean>(`${this.baseUrl}/register`, request);
  }
}
