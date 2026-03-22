import { Injectable } from '@angular/core';
import { environment } from '../../environment';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class UserService {

  private baseUrl = `${environment.BACK_END_URL}user`;

  constructor(private http: HttpClient) {}

  public deleteUserAccount(userID: number): Observable<boolean> {
    return this.http.delete<boolean>(`${this.baseUrl}/userID`, {});
  }
}
