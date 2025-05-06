import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { filter, Observable, Subject, take, takeUntil } from 'rxjs';
import { BooksApiStore, WikiStore } from '../../../store';
import { fadeAnimation } from '../../../constants';
import { BookListEntryComponent } from '../components/book-list-entry/book-list-entry.component';
import { MatCardModule } from '@angular/material/card';
import { WikiEntry } from '../../../models';

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

  public authorOfTheDay$: Observable<WikiEntry>;
  public authorOfTheDay: WikiEntry;

  public pages: any[] = [];
  public selectedPage: number = 0;
  public totalElements: number = 0;

  constructor(private _booksApiStore: BooksApiStore,
              private _wikiStore: WikiStore) {
    // this._booksApiStore.apiSearch('Stephen Graham Jones')
    this._booksApiStore.getPopularFiction();
    this._wikiStore.getAuthorOfTheDay('Kurt Vonnegut')
  }

  public ngOnInit(): void {
    this.booksResults$ = this._booksApiStore.select(s => s.popularFiction)
      .pipe(takeUntil(this.destroy$))
    this.booksResults$.subscribe(r => this.booksResults = r);

    this.authorOfTheDay$ = this._wikiStore.select(s => s.authorOfTheDay)
      .pipe(filter(r => !!r), take(1))
    this.authorOfTheDay$.subscribe(r => {this.authorOfTheDay = r; console.log(r)})
  }

  public pageChanged(e: any): void {

  }

  public ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

}
