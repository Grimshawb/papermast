import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, filter, map, take } from 'rxjs';
import { WikiEntry } from '../models/wiki-entry.model';
import { environment } from '../../environment';

@Injectable({
  providedIn: 'root'
})
export class WikiService {
  private baseUrl = `${environment.BACK_END_URL}wiki`;

  constructor(private http: HttpClient) {}

  getAuthorSummary(authorName: string): Observable<WikiEntry> {
    return this.http.get<WikiEntry>(`${this.baseUrl}/${authorName}`);
  }
}
