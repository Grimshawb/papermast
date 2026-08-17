import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { GENRES } from '../../../models';

@Component({
  selector: 'bookshelf-genre-directory',
  standalone: true,
  imports: [RouterLink],
  templateUrl: './genre-directory.component.html',
  styleUrl: './genre-directory.component.scss'
})
export class GenreDirectoryComponent {
  public readonly genres = GENRES;
}
