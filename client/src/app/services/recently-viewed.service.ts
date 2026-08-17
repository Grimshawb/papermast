import { isPlatformBrowser } from '@angular/common';
import { Inject, Injectable, PLATFORM_ID } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiBook, NytBook } from '../models';

interface StoredRecentBook extends ApiBook {
  viewedAt: string;
}

@Injectable({ providedIn: 'root' })
export class RecentlyViewedService {
  private readonly storageKey = 'papermast.recently-viewed';
  private readonly maximumBooks = 12;
  private readonly booksSubject = new BehaviorSubject<ApiBook[]>([]);

  public readonly books$ = this.booksSubject.asObservable();

  constructor(@Inject(PLATFORM_ID) private platformId: object) {
    this.booksSubject.next(this.read().map(({ viewedAt, ...book }) => book));
  }

  public record(book: NytBook, sourceBookID?: string, pageCount = 0): void {
    if (!isPlatformBrowser(this.platformId)) return;

    const id = sourceBookID || this.identifier(book) || this.fallbackID(book);
    const recentBook: StoredRecentBook = {
      id,
      authors: book.author ? [book.author] : [],
      categories: [],
      description: book.description || '',
      imageLinks: {
        thumbnail: book.bookImage || 'assets/book-placeholder.svg',
        smallThumbnail: book.bookImage || 'assets/book-placeholder.svg'
      },
      industryIdentifiers: book.isbns || [],
      maturityRating: '',
      language: 'en',
      pageCount,
      previewLink: '',
      printType: 'BOOK',
      publishedDate: undefined,
      publisher: book.publisher || '',
      subtitle: '',
      title: book.title,
      viewedAt: new Date().toISOString()
    };

    const books = [
      recentBook,
      ...this.read().filter(item => item.id !== id)
    ].slice(0, this.maximumBooks);

    localStorage.setItem(this.storageKey, JSON.stringify(books));
    this.booksSubject.next(books.map(({ viewedAt, ...item }) => item));
  }

  private read(): StoredRecentBook[] {
    if (!isPlatformBrowser(this.platformId)) return [];

    try {
      const value = localStorage.getItem(this.storageKey);
      const books = value ? JSON.parse(value) : [];
      return Array.isArray(books) ? books : [];
    } catch {
      return [];
    }
  }

  private identifier(book: NytBook): string | undefined {
    return book.isbns?.find(item => item.identifier)?.identifier;
  }

  private fallbackID(book: NytBook): string {
    return `${book.title}-${book.author}`.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
  }
}
