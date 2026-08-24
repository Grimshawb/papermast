import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { finalize, take } from 'rxjs';
import { BookEntry, BookEntryRequest } from '../../../../models';
import { BookEntriesService, ToasterService } from '../../../../services';

@Component({
  selector: 'shelf-book-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule,
    MatDatepickerModule, MatIconModule, MatInputModule, MatProgressBarModule, MatProgressSpinnerModule,
    MatSelectModule],
  templateUrl: './shelf-book-dialog.component.html',
  styleUrl: './shelf-book-dialog.component.scss'
})
export class ShelfBookDialogComponent {
  public readonly reviewMaxLength = 10000;
  public readonly statuses = ['To Be Read', 'Reading', 'Read', 'Did Not Finish', 'Not Interested'];
  public status: string;
  public pageCount: number;
  public pagesCompleted: number;
  public percentCompleted: number;
  public startDate: Date | null;
  public endDate: Date | null;
  public rating?: number;
  public userReview: string;
  public userInternalReview: string;
  public isSaving = false;

  constructor(
    @Inject(MAT_DIALOG_DATA) public entry: BookEntry,
    private dialogRef: MatDialogRef<ShelfBookDialogComponent, BookEntry>,
    private bookEntriesService: BookEntriesService,
    private toaster: ToasterService
  ) {
    this.status = entry.status;
    this.pageCount = entry.pageCount;
    this.pagesCompleted = entry.pagesCompleted;
    this.percentCompleted = entry.percentCompleted;
    this.startDate = this.toDateInputValue(entry.startDate);
    this.endDate = this.toDateInputValue(entry.endDate);
    this.rating = entry.rating;
    this.userReview = entry.userReview || '';
    this.userInternalReview = entry.userInternalReview || '';
  }

  public updatePages(value: number | string): void {
    this.pagesCompleted = this.clamp(Number(value), 0, this.pageCount || Number.MAX_SAFE_INTEGER);
    if (this.pageCount > 0) {
      this.percentCompleted = Math.round(this.pagesCompleted / this.pageCount * 100);
    }
  }

  public updatePageCount(value: number | string): void {
    this.pageCount = this.clamp(Number(value), 0, Number.MAX_SAFE_INTEGER);
    this.pagesCompleted = this.clamp(this.pagesCompleted, 0, this.pageCount || Number.MAX_SAFE_INTEGER);
    if (this.pageCount > 0) {
      this.percentCompleted = Math.round(this.pagesCompleted / this.pageCount * 100);
    }
  }

  public updatePercent(value: number | string): void {
    this.percentCompleted = this.clamp(Number(value), 0, 100);
    if (this.pageCount > 0) {
      this.pagesCompleted = Math.round(this.percentCompleted / 100 * this.pageCount);
    }
  }

  public save(): void {
    if (this.isSaving) return;
    this.isSaving = true;
    this.bookEntriesService.update(this.entry.entryID, this.toRequest())
      .pipe(take(1), finalize(() => this.isSaving = false))
      .subscribe(updatedEntry => {
        this.toaster.success(`${this.entry.title} updated.`);
        this.dialogRef.close(updatedEntry);
      });
  }

  public setRating(rating: number): void {
    this.rating = rating;
  }

  private toRequest(): BookEntryRequest {
    return {
      source: this.entry.source,
      sourceBookID: this.entry.sourceBookID,
      title: this.entry.title,
      authors: this.entry.authors,
      thumbnailUrl: this.entry.thumbnailUrl,
      isbn10: this.entry.isbn10,
      isbn13: this.entry.isbn13,
      status: this.status,
      pageCount: this.pageCount,
      pagesCompleted: this.pagesCompleted,
      percentCompleted: this.percentCompleted,
      rating: this.status === 'Read' ? this.rating : undefined,
      startDate: this.status === 'Reading' || this.status === 'Read' ? this.toRequestDate(this.startDate) : undefined,
      endDate: this.status === 'Read' ? this.toRequestDate(this.endDate) : undefined,
      userReview: this.status === 'Read' ? this.userReview : undefined,
      userInternalReview: this.status === 'Read' ? this.userInternalReview : undefined
    };
  }

  private toDateInputValue(value?: Date | string): Date | null {
    if (!value) return null;
    const datePart = value instanceof Date
      ? `${value.getUTCFullYear()}-${String(value.getUTCMonth() + 1).padStart(2, '0')}-${String(value.getUTCDate()).padStart(2, '0')}`
      : value.slice(0, 10);
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(datePart);
    if (!match) return null;
    const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    return Number.isNaN(date.getTime()) ? null : date;
  }

  private toRequestDate(value: Date | null): string | undefined {
    if (!value || Number.isNaN(value.getTime())) return undefined;
    const year = value.getFullYear();
    const month = String(value.getMonth() + 1).padStart(2, '0');
    const day = String(value.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private clamp(value: number, minimum: number, maximum: number): number {
    if (!Number.isFinite(value)) return minimum;
    return Math.min(maximum, Math.max(minimum, Math.round(value)));
  }
}
