
import { Component, OnDestroy, OnInit } from '@angular/core';
import { filter, Observable, Subject, take, takeUntil, tap } from 'rxjs';
import { BooksApiStore, NytStore, WikiStore } from '../../../store';
import { fadeAnimation } from '../../../constants';
import { BookListEntryComponent } from '../components/book-list-entry/book-list-entry.component';
import { MatCardModule } from '@angular/material/card';
import { ApiBook, BookSearchRequestDto, GENRES, WikiEntry } from '../../../models';
import { DailyAuthorComponent } from '../components/daily-author/daily-author.component';
import { DailyAuthors } from '../../../constants/daily-authors.enum';
import { NytService } from '../../../services/nyt.service';
import { ReadingGoal, User } from '../../../models';
import { AuthStore } from '../../../store/auth.store';
import { ReadingGoalsService, RecentlyViewedService } from '../../../services';
import { ReadingGoalWidgetComponent } from '../../shared/reading-goal-widget/reading-goal-widget.component';
import { Router, RouterLink } from '@angular/router';

@Component({
  selector: 'bookshelf-home-page',
  standalone: true,
  imports: [BookListEntryComponent, MatCardModule, DailyAuthorComponent, ReadingGoalWidgetComponent, RouterLink],
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
  public author: string;

  public pages: any[] = [];
  public selectedPage: number = 0;
  public totalElements: number = 0;
  public loggedInUser: User | undefined;
  public readingGoal: ReadingGoal | null = null;
  public recentlyViewedBooks: ApiBook[] = [];
  public readonly genres = GENRES;

  constructor(private _booksApiStore: BooksApiStore,
              private _wikiStore: WikiStore,
              private _nytStore: NytStore,
              private _authStore: AuthStore,
              private _readingGoalsService: ReadingGoalsService,
              private _recentlyViewedService: RecentlyViewedService,
              private _router: Router) {
    this.getDailyAuthor();
    this._booksApiStore.apiSearch({inauthor: this.author} as BookSearchRequestDto);
    this._nytStore.getAllBestsellerLists();
  }

  public ngOnInit(): void {
    this.booksResults$ = this._booksApiStore.select(s => s.searchResults)
      .pipe(takeUntil(this.destroy$))
    this.booksResults$.subscribe(r => this.booksResults = r);

    this.authorOfTheDay$ = this._wikiStore.select(s => s.authorOfTheDay)
      .pipe(tap(a => this.authorOfTheDay = a), takeUntil(this.destroy$))
    this.authorOfTheDay$.subscribe();

    this._authStore.select(s => s.loggedInUser)
      .pipe(takeUntil(this.destroy$))
      .subscribe(user => {
        this.loggedInUser = user;
        if (user) this.loadReadingGoal();
        else this.readingGoal = null;
      });

    this._recentlyViewedService.books$
      .pipe(takeUntil(this.destroy$))
      .subscribe(books => this.recentlyViewedBooks = books);
  }

  public pageChanged(e: any): void {

  }

  public openShelves(): void {
    this._router.navigate(['shelves']);
  }

  private loadReadingGoal(): void {
    this._readingGoalsService.get(new Date().getFullYear())
      .pipe(take(1))
      .subscribe({ next: goal => this.readingGoal = goal });
  }

  public async getDailyAuthor() {
    const authors = Object.values(DailyAuthors);
    const startDate = new Date("2024-01-01"); // fixed epoch
    const today = new Date();
    const daysSince = Math.floor(
      (today.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)
    );
    const index = daysSince % authors.length;
    this.author = authors[index].replace('_', ' ');
    this._wikiStore.getAuthorOfTheDay(this.author);

  }

  public ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

}
