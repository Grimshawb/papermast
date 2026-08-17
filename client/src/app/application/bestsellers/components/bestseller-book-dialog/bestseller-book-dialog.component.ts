import { CommonModule } from '@angular/common';
import { Component, DestroyRef, Inject, inject, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { defaultIfEmpty, finalize, take } from 'rxjs';
import { BookEntry, BookEntryRequest, IsbnType, NytBook, User } from '../../../../models';
import { BookEntriesService, ToasterService } from '../../../../services';
import { AuthStore } from '../../../../store';

export interface BestsellerBookDialogData {
  book: NytBook;
  eyebrow?: string;
  source?: string;
  sourceBookID?: string;
  pageCount?: number;
}

@Component({
  selector: 'bestseller-book-dialog',
  imports: [CommonModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule,
    MatProgressSpinnerModule, MatSelectModule],
  templateUrl: './bestseller-book-dialog.component.html',
  styleUrl: './bestseller-book-dialog.component.scss'
})
export class BestsellerBookDialogComponent implements OnInit {
  public readonly statuses = ['To Be Read', 'Reading', 'Read', 'Did Not Finish', 'Not Interested'];
  public entries: BookEntry[] = [];
  public loggedInUser: User | undefined;
  public isSaving = false;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    @Inject(MAT_DIALOG_DATA) public data: BestsellerBookDialogData,
    private dialogRef: MatDialogRef<BestsellerBookDialogComponent>,
    private bookEntriesService: BookEntriesService,
    private authStore: AuthStore,
    private toaster: ToasterService,
    private router: Router
  ) {}

  public get book(): NytBook {
    return this.data.book;
  }

  public get eyebrow(): string {
    return this.data.eyebrow || 'NYT Best Seller';
  }

  public ngOnInit(): void {
    this.authStore.select(state => state.loggedInUser)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(user => {
        this.loggedInUser = user;
        if (user) this.loadEntries();
      });
  }

  public get currentEntry(): BookEntry | undefined {
    const isbn10 = this.identifier(IsbnType.ISBN_10);
    const isbn13 = this.identifier(IsbnType.ISBN_13);
    const sourceBookID = this.data.sourceBookID || isbn13 || isbn10 || this.fallbackSourceID;
    return this.entries.find(entry =>
      (!!isbn13 && entry.isbn13 === isbn13) ||
      (!!isbn10 && entry.isbn10 === isbn10) ||
      (entry.source === (this.data.source || 'nyt-bestsellers') && entry.sourceBookID === sourceBookID));
  }

  public setStatus(status: string): void {
    if (!this.loggedInUser) {
      this.dialogRef.close();
      this.router.navigate(['/login']);
      return;
    }
    if (this.isSaving || status === this.currentEntry?.status) return;

    const existing = this.currentEntry;
    const request = this.toEntryRequest(status, existing);
    const operation = existing
      ? this.bookEntriesService.update(existing.entryID, request)
      : this.bookEntriesService.create(request);

    this.isSaving = true;
    operation.pipe(take(1), finalize(() => this.isSaving = false))
      .subscribe(entry => {
        this.entries = existing
          ? this.entries.map(item => item.entryID === entry.entryID ? entry : item)
          : [entry, ...this.entries];
        this.toaster.success(`${this.book.title} marked as ${entry.status}.`);
      });
  }

  public signIn(): void {
    this.dialogRef.close();
    this.router.navigate(['/login']);
  }

  private loadEntries(): void {
    this.bookEntriesService.getAll().pipe(take(1), defaultIfEmpty([]))
      .subscribe(entries => this.entries = entries);
  }

  private identifier(type: IsbnType): string | undefined {
    return this.book.isbns?.find(item => item.type === type)?.identifier || undefined;
  }

  private get fallbackSourceID(): string {
    return `${this.book.title}-${this.book.author}`.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-');
  }

  private toEntryRequest(status: string, existing?: BookEntry): BookEntryRequest {
    const isbn10 = this.identifier(IsbnType.ISBN_10);
    const isbn13 = this.identifier(IsbnType.ISBN_13);
    return {
      source: existing?.source || this.data.source || 'nyt-bestsellers',
      sourceBookID: existing?.sourceBookID || this.data.sourceBookID || isbn13 || isbn10 || this.fallbackSourceID,
      title: existing?.title || this.book.title,
      authors: existing?.authors || this.book.author,
      thumbnailUrl: existing?.thumbnailUrl || this.book.bookImage,
      isbn10: existing?.isbn10 || isbn10,
      isbn13: existing?.isbn13 || isbn13,
      status,
      pageCount: existing?.pageCount || this.data.pageCount || 0
    };
  }
}
