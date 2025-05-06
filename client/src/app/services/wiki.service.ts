import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, filter, map, take } from 'rxjs';
import { WikiEntry } from '../models/wiki-entry.model';

@Injectable({
  providedIn: 'root'
})
export class WikiService {

  private baseUrl = 'https://en.wikipedia.org/api/rest_v1/page/summary';

  constructor(private http: HttpClient) {}

  getAuthorSummary(authorName: string): Observable<WikiEntry> {
    const formatted = authorName.trim().replace(/ /g, '_');
    return this.http.get<WikiEntry>(`${this.baseUrl}/${formatted}`);
  }
}
