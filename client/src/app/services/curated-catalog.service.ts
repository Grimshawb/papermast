import { HttpClient, HttpContext } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environment';
import { CatalogImportPreview, CuratedCatalog } from '../models';
import { HANDLE_ERROR_LOCALLY } from '../interceptors/error-context';

@Injectable({ providedIn: 'root' })
export class CuratedCatalogService {
  private readonly baseUrl = `${environment.BACK_END_URL}curated-catalogs`;
  constructor(private http: HttpClient) {}

  public get(slug: string): Observable<CuratedCatalog> {
    return this.http.get<CuratedCatalog>(`${this.baseUrl}/${encodeURIComponent(slug)}`);
  }

  public getForAdmin(slug: string): Observable<CatalogImportPreview> {
    return this.http.get<CatalogImportPreview>(`${this.baseUrl}/${encodeURIComponent(slug)}/manage`, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }

  public import(slug: string, section: string, file: File): Observable<CatalogImportPreview> {
    const form = new FormData();
    form.append('file', file);
    form.append('section', section);
    return this.http.post<CatalogImportPreview>(`${this.baseUrl}/${encodeURIComponent(slug)}/imports`, form, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }

  public publish(slug: string, batchId: number): Observable<CuratedCatalog> {
    return this.http.post<CuratedCatalog>(`${this.baseUrl}/${encodeURIComponent(slug)}/imports/${batchId}/publish`, {});
  }

  public setCover(slug: string, batchId: number, isbn: string, url: string): Observable<CuratedCatalog> {
    return this.http.put<CuratedCatalog>(`${this.baseUrl}/${encodeURIComponent(slug)}/imports/${batchId}/books/${encodeURIComponent(isbn)}/cover`, { url }, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }

  public removeCover(slug: string, batchId: number, isbn: string): Observable<CuratedCatalog> {
    return this.http.delete<CuratedCatalog>(`${this.baseUrl}/${encodeURIComponent(slug)}/imports/${batchId}/books/${encodeURIComponent(isbn)}/cover`, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }

  public addBook(slug: string, batchId: number, section: string, isbn: string): Observable<CuratedCatalog> {
    return this.http.post<CuratedCatalog>(`${this.baseUrl}/${encodeURIComponent(slug)}/imports/${batchId}/books`, { section, isbn }, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }

  public removeBook(slug: string, batchId: number, isbn: string): Observable<CuratedCatalog> {
    return this.http.delete<CuratedCatalog>(`${this.baseUrl}/${encodeURIComponent(slug)}/imports/${batchId}/books/${encodeURIComponent(isbn)}`, {
      context: new HttpContext().set(HANDLE_ERROR_LOCALLY, true)
    });
  }
}
