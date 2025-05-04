import { Component, Input } from '@angular/core';
import { BooksApiStore } from '../../../../store';
import { Router } from '@angular/router';
import { ApiBook } from '../../../../models';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';

@Component({
  selector: 'bookshelf-book-list-entry',
  imports: [CommonModule, MatCardModule],
  templateUrl: './book-list-entry.component.html',
  styleUrl: './book-list-entry.component.scss'
})
export class BookListEntryComponent {

  @Input()
  public book: ApiBook | undefined;

  constructor(private _bookStore: BooksApiStore,
              private _router: Router) { }

  public subtitle(s: string): string {
    if (s && s.trim() !== '') {
      return (' : ' + s);
    } else {
        return '';
    }
  }

  public navigateToBook(): void {
    if (this.book) {
      this._bookStore.setSelectedBook(this.book);
      this._router.navigate(['book']);
    }
  }
}
