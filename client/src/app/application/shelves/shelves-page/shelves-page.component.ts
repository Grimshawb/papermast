import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { defaultIfEmpty, filter, finalize, take } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { BookEntry, ReadingGoal, User } from '../../../models';
import { AuthStore } from '../../../store/auth.store';
import { BookEntriesService } from '../../../services';
import { ShelfBookDialogComponent } from '../components/shelf-book-dialog/shelf-book-dialog.component';
import { ReadingGoalWidgetComponent } from '../../shared/reading-goal-widget/reading-goal-widget.component';
import { ReadingGoalDialogComponent } from '../components/reading-goal-dialog/reading-goal-dialog.component';
import { ReadingGoalsService } from '../../../services';

interface ShelfOption {
  label: string;
  status: string | null;
  icon: string;
}

@Component({
  selector: 'shelves-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatButtonModule, MatCardModule, MatFormFieldModule,
    MatDialogModule, MatIconModule, MatInputModule, MatProgressSpinnerModule, MatSelectModule,
    ReadingGoalWidgetComponent],
  templateUrl: './shelves-page.component.html',
  styleUrl: './shelves-page.component.scss',
})
export class ShelvesPageComponent implements OnInit {
  public readonly shelves: ShelfOption[] = [
    { label: 'All Books', status: null, icon: 'library_books' },
    { label: 'To Be Read', status: 'To Be Read', icon: 'bookmark' },
    { label: 'Reading', status: 'Reading', icon: 'auto_stories' },
    { label: 'Read', status: 'Read', icon: 'task_alt' },
    { label: 'Did Not Finish', status: 'Did Not Finish', icon: 'stop_circle' },
    { label: 'Not Interested', status: 'Not Interested', icon: 'visibility_off' }
  ];

  public entries: BookEntry[] = [];
  public selectedShelf: string | null = null;
  public libraryQuery = '';
  public sortBy = 'recent';
  public loggedInUser: User | undefined;
  public isLoading = false;
  public loadError: string | null = null;
  public readingGoal: ReadingGoal = {
    year: new Date().getFullYear(),
    targetBookCount: 0,
    completedBookCount: 0
  };
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private authStore: AuthStore,
    private bookEntriesService: BookEntriesService,
    private readingGoalsService: ReadingGoalsService,
    private dialog: MatDialog
  ) {}

  public ngOnInit(): void {
    this.authStore.select(state => state.loggedInUser)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(user => {
        this.loggedInUser = user;
        if (user) {
          this.loadLibrary();
          this.loadReadingGoal();
        }
        else {
          this.entries = [];
          this.isLoading = false;
        }
      });
  }

  public get visibleEntries(): BookEntry[] {
    const query = this.libraryQuery.trim().toLowerCase();
    const filtered = this.entries.filter(entry =>
      (!this.selectedShelf || entry.status === this.selectedShelf) &&
      (!query || entry.title.toLowerCase().includes(query) || entry.authors?.toLowerCase().includes(query)));

    return filtered.sort((left, right) => {
      switch (this.sortBy) {
        case 'title': return left.title.localeCompare(right.title);
        case 'author': return (left.authors || '').localeCompare(right.authors || '');
        case 'progress': return right.percentCompleted - left.percentCompleted;
        default: return new Date(right.updatedDate).getTime() - new Date(left.updatedDate).getTime();
      }
    });
  }

  public countFor(status: string | null): number {
    return status ? this.entries.filter(entry => entry.status === status).length : this.entries.length;
  }

  public selectShelf(status: string | null): void {
    this.selectedShelf = status;
  }

  public shelfHeading(): string {
    return this.shelves.find(shelf => shelf.status === this.selectedShelf)?.label || 'All Books';
  }

  public showDetails(entry: BookEntry): void {
    this.dialog.open(ShelfBookDialogComponent, {
      data: entry,
      width: 'min(760px, calc(100vw - 32px))',
      maxWidth: '760px',
      maxHeight: 'calc(var(--app-visual-viewport-height, 100dvh) - 16px)',
      panelClass: 'app-responsive-dialog',
      position: { top: 'calc(var(--app-visual-viewport-offset-top, 0px) + 8px)' },
      autoFocus: 'dialog'
    }).afterClosed()
      .pipe(take(1), filter((updatedEntry): updatedEntry is BookEntry => !!updatedEntry))
      .subscribe(updatedEntry => {
        this.entries = this.entries.map(item => item.entryID === updatedEntry.entryID ? updatedEntry : item);
      });
  }

  public retryLoad(): void {
    this.loadLibrary();
  }

  public editReadingGoal(): void {
    this.dialog.open(ReadingGoalDialogComponent, {
      data: this.readingGoal,
      width: 'min(480px, calc(100vw - 32px))',
      maxWidth: '480px',
      autoFocus: 'dialog'
    }).afterClosed()
      .pipe(take(1), filter((goal): goal is ReadingGoal => !!goal))
      .subscribe(goal => this.readingGoal = goal);
  }

  private loadReadingGoal(): void {
    this.readingGoalsService.get(this.readingGoal.year)
      .pipe(take(1))
      .subscribe({ next: goal => this.readingGoal = goal });
  }

  private loadLibrary(): void {
    if (this.isLoading) return;
    this.isLoading = true;
    this.loadError = null;
    this.bookEntriesService.getAll()
      .pipe(take(1), defaultIfEmpty(null), finalize(() => this.isLoading = false))
      .subscribe(entries => {
        if (entries === null) {
          this.loadError = 'We could not load your library. Please try again.';
          return;
        }
        this.entries = entries;
      });
  }

}
