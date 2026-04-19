import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { BooksApiStore } from '../../../store';
import { Observable, Subject, takeUntil, tap } from 'rxjs';
import { ApiBook } from '../../../models';

@Component({
  selector: 'book-details-page',
  imports: [CommonModule],
  templateUrl: './book-details-page.component.html',
  styleUrl: './book-details-page.component.scss',
})
export class BookDetailsPageComponent implements OnInit, OnDestroy {

  public selectedBook$: Observable<ApiBook>
  public selectedBook: ApiBook
  private destroy$: Subject<void> = new Subject<void>();

  constructor(private _bookStore: BooksApiStore) {}

  ngOnInit(): void {
    this.selectedBook$ = this._bookStore.select(s => s.selectedBook)
      .pipe(takeUntil(this.destroy$), tap(b => this.selectedBook = b));
  }

  ngOnDestroy(): void {
    this.destroy$.next(null);
    this.destroy$.complete();
  }
}
