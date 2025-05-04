import { Injectable } from '@angular/core';
import { ApiBook, BookStoreState } from '../models';
import { BehaviorSubject, filter, take } from 'rxjs';
import { BooksApiService } from '../services';

@Injectable({
  providedIn: 'root'
})

export class BooksApiStore {

  public constructor(private _bookService: BooksApiService) { }

  public state: BehaviorSubject<BookStoreState> = new BehaviorSubject({
    selectedBook: undefined,
    searchResults: undefined,
    popularFiction: undefined
  } as BookStoreState);

  public setSelectedBook(book: ApiBook | undefined): void {
    this.state.next({...this.state.getValue(), selectedBook: book} as BookStoreState);
  }

  public apiSearch(query: string): void {
    this._bookService.searchBooks(query)
      .pipe(filter(res => !!res), take(1))
      .subscribe(res => {
        this.state.next({...this.state.getValue(), searchResults: res?.items?.map(b => b.volumeInfo)} as BookStoreState);
      });
  }

  public getPopularFiction(): void {
    this._bookService.popularFiction()
      .pipe(take(1))
      .subscribe(res => {
        this.state.next({...this.state.getValue(), popularFiction: res?.items?.map(b => b.volumeInfo)} as BookStoreState);
      })
  }
}
