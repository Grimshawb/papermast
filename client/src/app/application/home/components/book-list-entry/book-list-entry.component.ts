import { Component, Input } from '@angular/core';
import { ApiBook, NytBook } from '../../../../models';

import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { BestsellerBookDialogComponent } from '../../../bestsellers/components/bestseller-book-dialog/bestseller-book-dialog.component';

@Component({
  selector: 'bookshelf-book-list-entry',
  imports: [MatCardModule, MatDialogModule],
  templateUrl: './book-list-entry.component.html',
  styleUrl: './book-list-entry.component.scss'
})
export class BookListEntryComponent {

  @Input()
  public book: ApiBook | undefined;

  @Input()
  public eyebrow = 'Author’s work';

  @Input()
  public interactive = true;

  constructor(private dialog: MatDialog) { }

  public subtitle(s: string): string {
    if (s && s.trim() !== '') {
      return (' : ' + s);
    } else {
        return '';
    }
  }

  public showDetails(): void {
    if (!this.book || !this.interactive) return;

    const dialogBook: NytBook = {
      ageGroup: '',
      amazonProductUrl: '',
      author: this.book.authors?.join(', ') || 'Unknown author',
      bookImage: this.book.imageLinks?.thumbnail || this.book.imageLinks?.smallThumbnail || 'assets/book-placeholder.svg',
      buyLinks: [],
      contributor: '',
      contributorNote: '',
      createdDate: undefined,
      description: this.book.description || '',
      isbns: this.book.industryIdentifiers || [],
      publisher: this.book.publisher || '',
      title: this.book.title,
      weeksOnList: 0
    };

    this.dialog.open(BestsellerBookDialogComponent, {
      data: {
        book: dialogBook,
        eyebrow: this.eyebrow,
        source: 'google-books',
        sourceBookID: this.book.id,
        pageCount: this.book.pageCount
      },
      width: 'min(760px, calc(100vw - 32px))',
      maxWidth: '760px',
      maxHeight: '90vh',
      autoFocus: 'dialog'
    });
  }
}
