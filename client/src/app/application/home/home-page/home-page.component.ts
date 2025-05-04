import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { Observable, Subject, takeUntil } from 'rxjs';
import { BooksApiStore } from '../../../store';
import { fadeAnimation } from '../../../constants';
import { BookListEntryComponent } from '../components/book-list-entry/book-list-entry.component';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'bookshelf-home-page',
  standalone: true,
  imports: [CommonModule, BookListEntryComponent, MatCardModule],
  templateUrl: './home-page.component.html',
  styleUrl: './home-page.component.scss',
  animations: [fadeAnimation]
})

export class HomePageComponent implements OnInit, OnDestroy {

  private destroy$: Subject<void> = new Subject<void>();

  public booksResults$!: Observable<any>;
  public booksResults!: any[];

  public pages: any[] = [];
  public selectedPage: number = 0;
  public totalElements: number = 0;

  constructor(private _booksApiStore: BooksApiStore) {
    // this._booksApiStore.apiSearch('Stephen Graham Jones')
    this._booksApiStore.getPopularFiction();
  }

  public ngOnInit(): void {
    this.booksResults$ = this._booksApiStore.state
      .pipe(takeUntil(this.destroy$));
    this.booksResults$.subscribe(r => {
      this.booksResults = r.popularFiction;
    })
  }

  public pageChanged(e: any): void {

  }

  public ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

}
