import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environment';
import { LibrarianRequestDto, LibrarianResponse } from '../models';
import { HANDLE_ERROR_LOCALLY } from '../interceptors/error-context';

@Injectable({ providedIn: 'root' })
export class LibrarianService {
  private readonly baseUrl = `${environment.BACK_END_URL}librarian`;

  constructor(private http: HttpClient) {}

  public recommend(request: LibrarianRequestDto): Observable<LibrarianResponse> {
    return this.http.post<LibrarianResponse>(`${this.baseUrl}/recommendations`, request, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }
}
