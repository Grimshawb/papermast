import { Injectable } from '@angular/core';
import { ApiBook, BookStoreState } from '../models';
import { filter, take } from 'rxjs';
import { BooksApiService } from '../services';
import { Store } from './store';

@Injectable({
  providedIn: 'root'
})

export class BooksApiStore extends Store<BookStoreState> {

  public constructor(private _bookService: BooksApiService) {
    super({
      selectedBook: undefined,
      searchResults: undefined,
      popularFiction: undefined
    });
   }


  public setSelectedBook(book: ApiBook | undefined): void {
    this.setState({ selectedBook: book });
  }

  public apiSearch(query: string): void {
    this._bookService.searchBooks(query)
      .pipe(filter(res => !!res), take(1))
      .subscribe(res => {
        this.setState({ searchResults: res?.items?.map(b => b.volumeInfo) });
      });
  }

  public getPopularFiction(): void {
    this._bookService.popularFiction()
      .pipe(take(1))
      .subscribe(res => {
        this.setState({ popularFiction: res?.items?.map(b => b.volumeInfo) });
      })
  }
}
