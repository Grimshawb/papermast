import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { DatePipe } from '@angular/common';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, finalize, map, of, switchMap } from 'rxjs';
import { CuratedCatalogSection, Genre, GENRES } from '../../../models';
import { CuratedCatalogService } from '../../../services';
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
  public curatedSections: CuratedCatalogSection[] = [];
  public isLoading = true;
  public loadFailed = false;
  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private route: ActivatedRoute,
    private curatedCatalogService: CuratedCatalogService
  ) {}

  public ngOnInit(): void {
    this.route.paramMap.pipe(
      switchMap(params => {
        const slug = params.get('slug') || '';
        this.genre = GENRES.find(item => item.slug === slug);
        this.curatedSections = [];
        this.loadFailed = false;
        this.isLoading = !!this.genre;

        if (!this.genre) return of([] as CuratedCatalogSection[]);
        return this.curatedCatalogService.get(this.genre.slug).pipe(
          map(catalog => catalog.sections ?? []),
          catchError(() => { this.loadFailed = true; return of([] as CuratedCatalogSection[]); }),
          finalize(() => this.isLoading = false)
        );
      }),
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(sections => this.curatedSections = sections);
  }
}
