import { Injectable } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { finalize } from 'rxjs';
import { Store } from './store';
import { LibrarianService } from '../services';
import { LibrarianStoreState } from '../models';

@Injectable({
  providedIn: 'root'
})
export class LibrarianStore extends Store<LibrarianStoreState> {
  public static readonly minQueryLength = 3;
  public static readonly maxQueryLength = 500;
  private static readonly resultCount = 5;

  public constructor(private librarianService: LibrarianService) {
    super({
      query: '',
      isLoading: false,
      hasSearched: false,
      errorMessage: null,
      recommendations: []
    });
  }

  public isQueryValid(query: string): boolean {
    const length = query.trim().length;
    return length >= LibrarianStore.minQueryLength && length <= LibrarianStore.maxQueryLength;
  }

  public search(query: string): void {
    const trimmed = query.trim();
    if (!this.isQueryValid(trimmed) || this.snapshot.isLoading) return;

    this.setState({ query: trimmed, isLoading: true, hasSearched: true, errorMessage: null });

    this.librarianService.recommend({ query: trimmed, resultCount: LibrarianStore.resultCount })
      .pipe(finalize(() => this.setState({ isLoading: false })))
      .subscribe({
        next: response => this.setState({ recommendations: response.recommendations, errorMessage: null }),
        error: (error: HttpErrorResponse) => this.setState({ recommendations: [], errorMessage: this.friendlyError(error) })
      });
  }

  public retry(): void {
    this.search(this.snapshot.query);
  }

  private friendlyError(error: HttpErrorResponse): string {
    switch (error.status) {
      case 400:
        return "We couldn't quite understand that request. Try rephrasing what you're in the mood for.";
      case 429:
        return "You're asking a little too quickly. Wait a moment and try again.";
      case 503:
        return 'The librarian is taking a short break. Please try again shortly.';
      default:
        return 'Something went wrong while fetching recommendations. Please try again.';
    }
  }
}
