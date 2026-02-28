import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, filter, map, take } from 'rxjs';
import { WikiEntry } from '../models/wiki-entry.model';
import { environment } from '../../environment';

@Injectable({
  providedIn: 'root'
})
export class NytService {
  private baseUrl = `${environment.BACK_END_URL}nyt`;

  constructor(private http: HttpClient) {}

  getAllBestSellerLists(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/all-lists`);
  }
}
