import { Component, Input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { GENRES } from '../../../../models';

@Component({
  selector: 'bookshelf-genre-switcher',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './genre-switcher.component.html',
  styleUrl: './genre-switcher.component.scss'
})
export class GenreSwitcherComponent {
  @Input({ required: true }) public currentGenre = '';
  public readonly genres = GENRES;
}
