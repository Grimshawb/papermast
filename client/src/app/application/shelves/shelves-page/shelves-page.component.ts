import { CommonModule } from '@angular/common';
import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { defaultIfEmpty, finalize, take } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { BookEntry, BookEntryRequest, User } from '../../../models';
import { AuthStore } from '../../../store/auth.store';
import { BookEntriesService, ToasterService } from '../../../services';

interface ShelfOption {
  label: string;
  status: string | null;
  icon: string;
}

@Component({
  selector: 'shelves-page',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, MatButtonModule, MatCardModule, MatFormFieldModule,
    MatIconModule, MatInputModule, MatProgressBarModule, MatProgressSpinnerModule, MatSelectModule],
  templateUrl: './shelves-page.component.html',
  styleUrl: './shelves-page.component.scss',
})
export class ShelvesPageComponent implements OnInit {
  public readonly statuses = ['To Be Read', 'Reading', 'Read', 'Did Not Finish', 'Not Interested'];
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
  public savingEntryID: number | null = null;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private authStore: AuthStore,
    private bookEntriesService: BookEntriesService,
    private toaster: ToasterService
  ) {}

  public ngOnInit(): void {
    this.authStore.select(state => state.loggedInUser)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(user => {
        this.loggedInUser = user;
        if (user) this.loadLibrary();
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

  public updateStatus(entry: BookEntry, status: string): void {
    if (status === entry.status || this.savingEntryID !== null) return;

    this.savingEntryID = entry.entryID;
    this.bookEntriesService.update(entry.entryID, this.toRequest(entry, status))
      .pipe(take(1), finalize(() => this.savingEntryID = null))
      .subscribe(updatedEntry => {
        this.entries = this.entries.map(item => item.entryID === updatedEntry.entryID ? updatedEntry : item);
        this.toaster.success(`${entry.title} moved to ${updatedEntry.status}.`);
      });
  }

  public retryLoad(): void {
    this.loadLibrary();
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

  private toRequest(entry: BookEntry, status: string): BookEntryRequest {
    return {
      source: entry.source,
      sourceBookID: entry.sourceBookID,
      title: entry.title,
      authors: entry.authors,
      thumbnailUrl: entry.thumbnailUrl,
      isbn10: entry.isbn10,
      isbn13: entry.isbn13,
      status,
      pageCount: entry.pageCount
    };
  }
}
