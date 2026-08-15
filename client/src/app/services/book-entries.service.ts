import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environment.prod';
import { BookEntry, BookEntryRequest } from '../models';

@Injectable({ providedIn: 'root' })
export class BookEntriesService {
  private readonly baseUrl = `${environment.BACK_END_URL}bookentries`;

  constructor(private http: HttpClient) {}

  public getAll(): Observable<BookEntry[]> {
    return this.http.get<BookEntry[]>(this.baseUrl);
  }

  public create(request: BookEntryRequest): Observable<BookEntry> {
    return this.http.post<BookEntry>(this.baseUrl, request);
  }

  public update(entryID: number, request: BookEntryRequest): Observable<BookEntry> {
    return this.http.put<BookEntry>(`${this.baseUrl}/${entryID}`, request);
  }
}
