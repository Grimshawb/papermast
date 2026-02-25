import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { filter, Observable, Subject, take, takeUntil, tap } from 'rxjs';
import { BooksApiStore, WikiStore } from '../../../store';
import { fadeAnimation } from '../../../constants';
import { BookListEntryComponent } from '../components/book-list-entry/book-list-entry.component';
import { MatCardModule } from '@angular/material/card';
import { BookSearchRequestDto, WikiEntry } from '../../../models';
import { DailyAuthorComponent } from '../components/daily-author/daily-author.component';
import { DailyAuthors } from '../../../constants/daily-authors.enum';

@Component({
  selector: 'bookshelf-home-page',
  standalone: true,
  imports: [CommonModule, BookListEntryComponent, MatCardModule, DailyAuthorComponent],
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
    this._booksApiStore.apiSearch({inauthor: 'Stephen Graham Jones'} as BookSearchRequestDto);
    // this._booksApiStore.getPopularFiction();
    this.getDailyAuthor();
  }

  public ngOnInit(): void {
    this.booksResults$ = this._booksApiStore.select(s => s.searchResults)
      .pipe(takeUntil(this.destroy$))
    this.booksResults$.subscribe(r => this.booksResults = r);

    this.authorOfTheDay$ = this._wikiStore.select(s => s.authorOfTheDay)
      .pipe(tap(a => this.authorOfTheDay = a), takeUntil(this.destroy$))
    this.authorOfTheDay$.subscribe();
  }

  public pageChanged(e: any): void {

  }

  public async getDailyAuthor() {
    const authors = Object.values(DailyAuthors);
    const startDate = new Date("2024-01-01"); // fixed epoch
    const today = new Date();
    const daysSince = Math.floor(
      (today.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
    );
    const index = daysSince % authors.length;
    this._wikiStore.getAuthorOfTheDay(authors[index]);
  }

  public ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

}
