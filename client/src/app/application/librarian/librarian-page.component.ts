import { Component, DestroyRef, inject, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MOBILE_BREAKPOINT } from '../../constants';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { LibrarianRecommendation, User } from '../../models';
import { LibrarianStore } from '../../store/librarian.store';
import { AuthStore } from '../../store/auth.store';

@Component({
  selector: 'librarian-page',
  standalone: true,
  imports: [FormsModule, RouterLink, MatButtonModule, MatCardModule, MatFormFieldModule, MatIconModule,
    MatInputModule, MatProgressSpinnerModule],
  templateUrl: './librarian-page.component.html',
  styleUrl: './librarian-page.component.scss'
})
export class LibrarianPageComponent implements OnInit {
  public readonly minLength = LibrarianStore.minQueryLength;
  public readonly maxLength = LibrarianStore.maxQueryLength;

  public query = '';
  public isMobile = false;
  public loggedInUser: User | undefined;

  public isLoading = false;
  public hasSearched = false;
  public errorMessage: string | null = null;
  public recommendations: LibrarianRecommendation[] = [];

  private readonly destroyRef = inject(DestroyRef);

  constructor(
    private librarianStore: LibrarianStore,
    private authStore: AuthStore,
    private breakpointObserver: BreakpointObserver
  ) {}

  public ngOnInit(): void {
    this.query = this.librarianStore.snapshot.query;

    this.librarianStore.state$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(state => {
        this.isLoading = state.isLoading;
        this.hasSearched = state.hasSearched;
        this.errorMessage = state.errorMessage;
        this.recommendations = state.recommendations;
      });

    this.authStore.select(state => state.loggedInUser)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(user => this.loggedInUser = user);

    this.breakpointObserver.observe([MOBILE_BREAKPOINT])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(result => this.isMobile = result.matches);
  }

  public get isQueryValid(): boolean {
    return this.librarianStore.isQueryValid(this.query);
  }

  public submit(): void {
    this.librarianStore.search(this.query);
  }

  public retry(): void {
    this.librarianStore.retry();
  }

  public authorsLabel(recommendation: LibrarianRecommendation): string {
    return recommendation.authors?.length ? recommendation.authors.join(', ') : 'Unknown author';
  }

  public coverUrl(recommendation: LibrarianRecommendation): string | null {
    const coverId = recommendation.coverIds?.[0];
    return coverId ? `https://covers.openlibrary.org/b/id/${coverId}-M.jpg` : null;
  }

  public openLibraryUrl(recommendation: LibrarianRecommendation): string {
    return `https://openlibrary.org${recommendation.workKey}`;
  }
}
