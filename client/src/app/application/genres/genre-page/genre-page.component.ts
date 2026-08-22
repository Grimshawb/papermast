import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, defaultIfEmpty, finalize, map, of, switchMap } from 'rxjs';
import { ApiBook, CuratedCatalogSection, Genre, GENRES } from '../../../models';
import { BooksApiService, CuratedCatalogService } from '../../../services';
import { BookListEntryComponent } from '../../home/components/book-list-entry/book-list-entry.component';

@Component({
  selector: 'bookshelf-genre-page',
  standalone: true,
  imports: [RouterLink, DatePipe, BookListEntryComponent],
  templateUrl: './genre-page.component.html',
  styleUrl: './genre-page.component.scss'
})
export class GenrePageComponent implements OnInit {
  public genre: Genre | undefined;
  public books: ApiBook[] = [];
  public curatedSections: CuratedCatalogSection[] = [];
  public isCurated = false;
  public isLoading = true;
  public loadFailed = false;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private route: ActivatedRoute,
    private booksApiService: BooksApiService,
    private curatedCatalogService: CuratedCatalogService
  ) {}

  public ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => {
        const slug = params.get('slug') || '';
        this.genre = GENRES.find(item => item.slug === slug);
        this.books = [];
        this.curatedSections = [];
        this.isCurated = false;
        this.loadFailed = false;
        this.isLoading = !!this.genre;

        if (!this.genre) return of([] as ApiBook[]);
        return this.curatedCatalogService.get(this.genre.slug).pipe(
          defaultIfEmpty(null),
          switchMap(catalog => {
            if (catalog?.publishedAt || this.genre?.slug === 'horror') {
              this.isCurated = true;
              this.curatedSections = catalog?.sections ?? [];
              return of([] as ApiBook[]);
            }

            return this.booksApiService.genre(this.genre!.slug).pipe(
              defaultIfEmpty(null),
              map(books => {
                if (books === null) {
                  this.loadFailed = true;
                  return [] as ApiBook[];
                }
                return books;
              })
            );
          }),
          catchError(() => { this.loadFailed = true; return of([] as ApiBook[]); }),
          finalize(() => this.isLoading = false)
        );
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(books => this.books = books);
  }
}
