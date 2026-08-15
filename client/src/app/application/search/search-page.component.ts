import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { defaultIfEmpty, finalize, forkJoin, map, Observable, take } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ApiBook, BookEntry, BookEntryRequest, BookSearchRequestDto, IsbnType, User } from '../../models';
import { AuthStore } from '../../store/auth.store';
import { BookEntriesService, BooksApiService, ToasterService } from '../../services';

@Component({
  selector: 'search-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatButtonModule, MatCardModule, MatFormFieldModule,
    MatIconModule, MatInputModule, MatProgressSpinnerModule, MatSelectModule],
  templateUrl: './search-page.component.html',
  styleUrl: './search-page.component.scss'
})
export class SearchPageComponent implements OnInit {
  public readonly statuses = ['To Be Read', 'Reading', 'Read', 'Did Not Finish', 'Not Interested'];
  public readonly searchTypes = [
    { value: 'all', label: 'All' },
    { value: 'title', label: 'Title' },
    { value: 'author', label: 'Author' },
    { value: 'isbn', label: 'ISBN' }
  ];
  public query = '';
  public searchType = 'all';
  public results: ApiBook[] = [];
  public entries: BookEntry[] = [];
  public loggedInUser: User | undefined;
  public isSearching = false;
  public hasSearched = false;
  public savingBookID: string | null = null;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private booksApiService: BooksApiService,
    private bookEntriesService: BookEntriesService,
    private authStore: AuthStore,
    private toaster: ToasterService,
    private router: Router
  ) {}

  public ngOnInit(): void {
    this.authStore.select(state => state.loggedInUser)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(user => {
        this.loggedInUser = user;
        if (user) this.loadEntries();
        else this.entries = [];
      });
  }

  public search(): void {
    const query = this.query.trim();
    if (!query || this.isSearching) return;

    this.isSearching = true;
    this.hasSearched = true;
    this.createSearch(query)
      .pipe(defaultIfEmpty([]), finalize(() => this.isSearching = false))
      .subscribe(results => this.results = results);
  }

  private createSearch(query: string): Observable<ApiBook[]> {
    const isbn = this.normalizedIsbn(query);

    if (this.searchType === 'isbn' || (this.searchType === 'all' && isbn)) {
      return this.booksApiService.search({ isbn: isbn || query } as BookSearchRequestDto);
    }
    if (this.searchType === 'title') {
      return this.booksApiService.search({ intitle: query } as BookSearchRequestDto);
    }
    if (this.searchType === 'author') {
      return this.booksApiService.search({ inauthor: query } as BookSearchRequestDto);
    }

    return forkJoin({
      title: this.booksApiService.search({ intitle: query } as BookSearchRequestDto)
        .pipe(defaultIfEmpty([])),
      author: this.booksApiService.search({ inauthor: query } as BookSearchRequestDto)
        .pipe(defaultIfEmpty([]))
    }).pipe(map(({ title, author }) => this.rankResults([...title, ...author], query)));
  }

  private normalizedIsbn(query: string): string | null {
    const normalized = query.replace(/[\s-]/g, '').toUpperCase();
    return /^(?:\d{9}[\dX]|97[89]\d{10})$/.test(normalized) ? normalized : null;
  }

  private rankResults(results: ApiBook[], query: string): ApiBook[] {
    const uniqueResults = new Map<string, ApiBook>();
    for (const book of results) {
      if (book.id && !uniqueResults.has(book.id)) uniqueResults.set(book.id, book);
    }

    return [...uniqueResults.values()]
      .map(book => ({ book, score: this.relevanceScore(book, query) }))
      .sort((left, right) => right.score - left.score)
      .map(result => result.book);
  }

  private relevanceScore(book: ApiBook, query: string): number {
    const normalizedQuery = this.normalizeText(query);
    const title = this.normalizeText(book.title || '');
    const authors = (book.authors || []).map(author => this.normalizeText(author));
    const queryTerms = normalizedQuery.split(' ').filter(Boolean);
    let score = 0;

    if (title === normalizedQuery) score += 1000;
    else if (title.startsWith(normalizedQuery)) score += 600;
    else if (title.includes(normalizedQuery)) score += 400;

    if (authors.some(author => author === normalizedQuery)) score += 900;
    else if (authors.some(author => author.startsWith(normalizedQuery))) score += 550;
    else if (authors.some(author => author.includes(normalizedQuery))) score += 350;

    const titleTermMatches = queryTerms.filter(term => title.includes(term)).length;
    const authorTermMatches = queryTerms.filter(term => authors.some(author => author.includes(term))).length;
    if (queryTerms.length) {
      score += Math.round((titleTermMatches / queryTerms.length) * 200);
      score += Math.round((authorTermMatches / queryTerms.length) * 180);
    }

    if (book.industryIdentifiers?.length) score += 20;
    if (book.imageLinks?.thumbnail || book.imageLinks?.smallThumbnail) score += 10;
    return score;
  }

  private normalizeText(value: string): string {
    return value
      .normalize('NFKD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-zA-Z0-9]+/g, ' ')
      .trim()
      .toLowerCase();
  }

  public entryFor(book: ApiBook): BookEntry | undefined {
    const request = this.toEntryRequest(book, 'To Be Read');
    return this.entries.find(entry =>
      (!!request.isbn13 && entry.isbn13 === request.isbn13) ||
      (!!request.isbn10 && entry.isbn10 === request.isbn10) ||
      (entry.source === request.source && entry.sourceBookID === request.sourceBookID));
  }

  public setStatus(book: ApiBook, status: string): void {
    if (!this.loggedInUser) {
      this.router.navigate(['/login']);
      return;
    }

    const existing = this.entryFor(book);
    const request = this.toEntryRequest(book, status);
    const operation = existing
      ? this.bookEntriesService.update(existing.entryID, request)
      : this.bookEntriesService.create(request);

    this.savingBookID = book.id;
    operation.pipe(take(1), finalize(() => this.savingBookID = null))
      .subscribe(entry => {
        this.entries = existing
          ? this.entries.map(item => item.entryID === entry.entryID ? entry : item)
          : [entry, ...this.entries];
        this.toaster.success(`${book.title} marked as ${entry.status}.`);
      });
  }

  private loadEntries(): void {
    this.bookEntriesService.getAll()
      .pipe(take(1), defaultIfEmpty([]))
      .subscribe(entries => this.entries = entries);
  }

  private toEntryRequest(book: ApiBook, status: string): BookEntryRequest {
    const identifiers = book.industryIdentifiers || [];
    const identifier = (type: IsbnType) => identifiers.find(item =>
      item.type === type || (item.type as string).toUpperCase() === type.toUpperCase())?.identifier;

    return {
      source: 'google-books',
      sourceBookID: book.id,
      title: book.title,
      authors: book.authors?.join(', '),
      thumbnailUrl: book.imageLinks?.thumbnail || book.imageLinks?.smallThumbnail,
      isbn10: identifier(IsbnType.ISBN_10),
      isbn13: identifier(IsbnType.ISBN_13),
      status,
      pageCount: book.pageCount || 0
    };
  }
}
