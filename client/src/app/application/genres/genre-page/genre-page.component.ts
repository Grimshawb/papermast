import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, defaultIfEmpty, finalize, map, of, switchMap } from 'rxjs';
import { ApiBook, Genre, GENRES } from '../../../models';
import { BooksApiService } from '../../../services';
import { BookListEntryComponent } from '../../home/components/book-list-entry/book-list-entry.component';

@Component({
  selector: 'bookshelf-genre-page',
  standalone: true,
  imports: [RouterLink, BookListEntryComponent],
  templateUrl: './genre-page.component.html',
  styleUrl: './genre-page.component.scss'
})
export class GenrePageComponent implements OnInit {
  public genre: Genre | undefined;
  public books: ApiBook[] = [];
  public isLoading = true;
  public loadFailed = false;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private route: ActivatedRoute,
    private booksApiService: BooksApiService
  ) {}

  public ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => {
        const slug = params.get('slug') || '';
        this.genre = GENRES.find(item => item.slug === slug);
        this.books = [];
        this.loadFailed = false;
        this.isLoading = !!this.genre;

        if (!this.genre) return of([] as ApiBook[]);
        return this.booksApiService.genre(this.genre.slug).pipe(
          // The global HTTP interceptor completes failed requests without an error.
          // Preserve a distinct failure state instead of presenting that as zero results.
          defaultIfEmpty(null),
          map(books => {
            if (books === null) {
              this.loadFailed = true;
              return [] as ApiBook[];
            }
            return books;
          }),
          catchError(() => {
            this.loadFailed = true;
            return of([] as ApiBook[]);
          }),
          finalize(() => this.isLoading = false)
        );
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(books => this.books = books);
  }
}
