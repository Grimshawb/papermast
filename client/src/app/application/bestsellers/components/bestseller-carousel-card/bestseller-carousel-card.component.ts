
import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { NytBook } from '../../../../models';
import { BestsellerBookDialogComponent } from '../bestseller-book-dialog/bestseller-book-dialog.component';

@Component({
  selector: 'bestseller-carousel-card',
  imports: [MatButtonModule, MatCardModule, MatDialogModule],
  templateUrl: './bestseller-carousel-card.component.html',
  styleUrl: './bestseller-carousel-card.component.scss'
})
export class BestsellerCarouselCardComponent {

  @Input() book: NytBook = undefined;

  constructor(private dialog: MatDialog) {}

  public showDetails(): void {
    if (!this.book) return;

    this.dialog.open(BestsellerBookDialogComponent, {
      data: { book: this.book },
      width: 'min(760px, calc(100vw - 32px))',
      maxWidth: '760px',
      maxHeight: '90vh',
      autoFocus: 'dialog'
    });
  }

}
