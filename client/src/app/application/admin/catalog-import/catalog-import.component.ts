import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { catchError, finalize, of } from 'rxjs';
import { CatalogImportError, CatalogImportPreview, CuratedCatalogBook, GENRES } from '../../../models';
import { CuratedCatalogService, ToasterService } from '../../../services';
import { BookListEntryComponent } from '../../home/components/book-list-entry/book-list-entry.component';

type SectionKey = 'popular' | 'upcoming';

@Component({
  selector: 'bookshelf-catalog-import',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatIconModule, MatSelectModule, MatFormFieldModule, BookListEntryComponent],
  templateUrl: './catalog-import.component.html',
  styleUrl: './catalog-import.component.scss'
})
export class CatalogImportComponent implements OnInit {
  public readonly genres = GENRES;
  public selectedGenre = 'horror';
  public selectedSection: SectionKey = 'popular';
  public selectedFile?: File;
  public errors: CatalogImportError[] = [];
  public catalog?: CatalogImportPreview;
  public isDraft = false;
  public isLoadingCatalog = false;
  public isUploading = false;
  public isPublishing = false;
  public editingCoverIsbn?: string;
  public coverUrl = '';
  public coverError = '';
  public isSavingCover = false;
  public addIsbn = '';
  public addError = '';
  public isAddingBook = false;
  public removingIsbn?: string;

  constructor(private catalogs: CuratedCatalogService, private toaster: ToasterService) {}

  public ngOnInit(): void { this.loadPublishedCatalog(); }

  public changeGenre(): void {
    this.selectedFile = undefined;
    this.errors = [];
    this.cancelCoverEdit();
    this.addIsbn = '';
    this.addError = '';
    this.loadPublishedCatalog();
  }

  public changeSection(): void {
    this.selectedFile = undefined;
    this.errors = [];
  }

  public selectFile(event: Event): void {
    this.selectedFile = (event.target as HTMLInputElement).files?.[0];
    this.errors = [];
  }

  public upload(): void {
    if (!this.selectedFile) return;
    this.isUploading = true;
    this.errors = [];
    this.catalogs.import(this.selectedGenre, this.selectedSection, this.selectedFile)
      .pipe(finalize(() => this.isUploading = false))
      .subscribe({
        next: preview => { this.catalog = preview; this.errors = preview.errors ?? []; this.isDraft = true; },
        error: (error: HttpErrorResponse) => this.errors = error.error?.errors
          ?? [{ row: 1, field: 'file', message: 'The upload could not be processed.' }]
      });
  }

  public publish(): void {
    if (!this.catalog || !this.isDraft) return;
    this.isPublishing = true;
    this.catalogs.publish(this.selectedGenre, this.catalog.batchId)
      .pipe(finalize(() => this.isPublishing = false))
      .subscribe(() => { this.toaster.success('The section is now live.'); this.selectedFile = undefined; this.loadPublishedCatalog(); });
  }

  public editCover(book: CuratedCatalogBook): void {
    this.editingCoverIsbn = book.isbn13;
    this.coverUrl = book.imageLinks?.thumbnail || '';
    this.coverError = '';
  }

  public cancelCoverEdit(): void {
    this.editingCoverIsbn = undefined;
    this.coverUrl = '';
    this.coverError = '';
  }

  public coverPreviewFailed(): void { this.coverError = 'The browser could not load this image URL.'; }

  public saveCover(): void {
    if (!this.catalog || !this.editingCoverIsbn) return;
    this.coverError = '';
    this.isSavingCover = true;
    this.catalogs.setCover(this.selectedGenre, this.catalog.batchId, this.editingCoverIsbn, this.coverUrl.trim())
      .pipe(finalize(() => this.isSavingCover = false))
      .subscribe({
        next: catalog => { this.catalog!.catalog = catalog; this.cancelCoverEdit(); this.toaster.success('Cover URL saved.'); },
        error: (error: HttpErrorResponse) => this.coverError = error.error?.message ?? 'The cover URL could not be saved.'
      });
  }

  public removeCover(): void {
    if (!this.catalog || !this.editingCoverIsbn) return;
    this.coverError = '';
    this.isSavingCover = true;
    this.catalogs.removeCover(this.selectedGenre, this.catalog.batchId, this.editingCoverIsbn)
      .pipe(finalize(() => this.isSavingCover = false))
      .subscribe({
        next: catalog => { this.catalog!.catalog = catalog; this.cancelCoverEdit(); this.toaster.success('Cover override removed.'); },
        error: () => this.coverError = 'The cover override could not be removed.'
      });
  }

  public addBook(): void {
    if (!this.catalog || !this.isDraft || !this.addIsbn.trim()) return;
    this.addError = '';
    this.isAddingBook = true;
    this.catalogs.addBook(this.selectedGenre, this.catalog.batchId, this.selectedSection, this.addIsbn.trim())
      .pipe(finalize(() => this.isAddingBook = false))
      .subscribe({
        next: catalog => { this.catalog!.catalog = catalog; this.addIsbn = ''; this.toaster.success('Book added to the draft.'); },
        error: (error: HttpErrorResponse) => this.addError = error.error?.message ?? 'The book could not be added.'
      });
  }

  public discardBook(book: CuratedCatalogBook): void {
    if (!this.catalog || !this.isDraft) return;
    this.removingIsbn = book.isbn13;
    this.catalogs.removeBook(this.selectedGenre, this.catalog.batchId, book.isbn13)
      .pipe(finalize(() => this.removingIsbn = undefined))
      .subscribe({
        next: catalog => { this.catalog!.catalog = catalog; this.toaster.success('Book discarded from the draft.'); },
        error: () => this.toaster.error('The book could not be discarded.')
      });
  }

  private loadPublishedCatalog(): void {
    this.isLoadingCatalog = true;
    this.catalog = undefined;
    this.isDraft = false;
    this.catalogs.getForAdmin(this.selectedGenre).pipe(
      catchError(() => of(undefined)),
      finalize(() => this.isLoadingCatalog = false)
    ).subscribe(catalog => this.catalog = catalog);
  }
}
