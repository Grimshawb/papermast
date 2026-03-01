import { CommonModule } from '@angular/common';
import { Component, Input} from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { NytBook } from '../../../../models';

@Component({
  selector: 'bestseller-carousel-card',
  imports: [CommonModule, MatButtonModule, MatCardModule],
  templateUrl: './bestseller-carousel-card.component.html',
  styleUrl: './bestseller-carousel-card.component.scss'
})
export class BestsellerCarouselCardComponent {

  @Input() book: NytBook = undefined;

}
