import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environment.prod';
import { ReadingGoal, ReadingGoalRequest } from '../models';

@Injectable({ providedIn: 'root' })
export class ReadingGoalsService {
  private readonly baseUrl = `${environment.BACK_END_URL}readinggoals`;

  constructor(private http: HttpClient) {}

  public get(year: number): Observable<ReadingGoal> {
    return this.http.get<ReadingGoal>(`${this.baseUrl}/${year}`);
  }

  public save(request: ReadingGoalRequest): Observable<ReadingGoal> {
    return this.http.put<ReadingGoal>(this.baseUrl, request);
  }
}
