import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { configureTestBed } from '@testing';
import { environment } from '../../../environment';
import { LibrarianRecommendation, User } from '../../models';
import { AuthStore } from '../../store/auth.store';
import { LibrarianStore } from '../../store/librarian.store';

import { LibrarianPageComponent } from './librarian-page.component';

describe('LibrarianPageComponent', () => {
  let component: LibrarianPageComponent;
  let fixture: ComponentFixture<LibrarianPageComponent>;
  let http: HttpTestingController;
  let authStore: AuthStore;
  let librarianStore: LibrarianStore;

  const endpoint = `${environment.BACK_END_URL}librarian/recommendations`;
  const loggedInUser = { userID: 1, email: 'brad@example.com' } as User;

  const recommendation: LibrarianRecommendation = {
    workKey: '/works/OL123W',
    title: 'Example',
    authors: ['Author'],
    genres: ['fantasy'],
    description: 'Description',
    editionKey: '/books/OL123M',
    coverIds: [123],
    isbn10: [],
    isbn13: [],
    publicationDate: '2001',
    pageCount: 320,
    reason: 'Why this fits the request.'
  };

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [LibrarianPageComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(LibrarianPageComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    authStore = TestBed.inject(AuthStore);
    librarianStore = TestBed.inject(LibrarianStore);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('desktop, logged out', () => {
    beforeEach(() => {
      component.isMobile = false;
      fixture.detectChanges();
    });

    it('shows no search form and prompts the visitor to log in', () => {
      expect(fixture.nativeElement.querySelector('.librarian-form')).toBeNull();

      const text = (fixture.nativeElement as HTMLElement).textContent || '';
      expect(text).toContain('Log in to ask the librarian');

      const loginLink = fixture.nativeElement.querySelector('a[routerLink="/login"]') as HTMLAnchorElement;
      expect(loginLink).toBeTruthy();
    });
  });

  describe('desktop, logged in', () => {
    beforeEach(() => {
      component.isMobile = false;
      (authStore as any).setState({ loggedInUser });
      fixture.detectChanges();
    });

    it('shows no search form and points to the header search instead', () => {
      expect(fixture.nativeElement.querySelector('.librarian-form')).toBeNull();
      const text = (fixture.nativeElement as HTMLElement).textContent || '';
      expect(text).toContain('search bar in the header');
    });

    it('renders recommendations placed into the store by the header search', () => {
      librarianStore.search('Something funny and weird.');
      http.expectOne(endpoint).flush({ recommendations: [recommendation], elapsedMs: 12 });
      fixture.detectChanges();

      const text = (fixture.nativeElement as HTMLElement).textContent || '';
      expect(text).toContain('Example');
      expect(text).toContain('Why this fits the request.');
    });
  });

  describe('mobile', () => {
    beforeEach(() => {
      component.isMobile = true;
      (authStore as any).setState({ loggedInUser });
      fixture.detectChanges();
    });

    it('shows the on-page search form when logged in', () => {
      expect(fixture.nativeElement.querySelector('.librarian-form')).toBeTruthy();
    });

    it('does not expose the search form when logged out', () => {
      (authStore as any).setState({ loggedInUser: undefined });
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.librarian-form')).toBeNull();
      expect((fixture.nativeElement as HTMLElement).textContent).toContain('Log in to ask the librarian');
    });

    it('does not submit an invalid query', () => {
      component.query = 'hi';
      component.submit();
      http.expectNone(endpoint);
    });

    it('serializes the trimmed query, renders results, and handles missing metadata', () => {
      component.query = '  Something funny and weird.  ';
      component.submit();

      const request = http.expectOne(endpoint);
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toEqual({ query: 'Something funny and weird.', resultCount: 5 });

      const sparse: LibrarianRecommendation = {
        workKey: '/works/OL999W',
        title: 'Mystery Book',
        authors: [],
        genres: [],
        description: '',
        coverIds: [],
        isbn10: [],
        isbn13: [],
        reason: 'A solid pick.'
      };

      request.flush({ recommendations: [sparse], elapsedMs: 10 });
      fixture.detectChanges();

      const cover = fixture.nativeElement.querySelector('.recommendation-card img') as HTMLImageElement;
      expect(cover.src).toContain('assets/book-placeholder.svg');

      const text = (fixture.nativeElement as HTMLElement).textContent || '';
      expect(text).toContain('Unknown author');
      expect(text).not.toContain('undefined');
      expect(text).not.toContain('null');
    });

    it('enters a loading state and ignores a second submission while in flight', () => {
      component.query = 'Something funny and weird.';
      component.submit();
      expect(component.isLoading).toBeTrue();

      component.submit();
      const pending = http.match(endpoint);
      expect(pending.length).toBe(1);

      pending[0].flush({ recommendations: [recommendation], elapsedMs: 5 });
      expect(component.isLoading).toBeFalse();
    });

    it('shows a nontechnical message and retry option for a 429 response', () => {
      component.query = 'Something funny and weird.';
      component.submit();
      http.expectOne(endpoint).flush('Too many requests', { status: 429, statusText: 'Too Many Requests' });
      fixture.detectChanges();

      expect(component.errorMessage).toContain('too quickly');
      const retryButton = fixture.nativeElement.querySelector('.error-state button') as HTMLButtonElement;
      expect(retryButton).toBeTruthy();
    });

    it('shows a nontechnical message for a 503 response and clears it on retry', () => {
      component.query = 'Something funny and weird.';
      component.submit();
      http.expectOne(endpoint).flush('Unavailable', { status: 503, statusText: 'Service Unavailable' });
      fixture.detectChanges();
      expect(component.errorMessage).toContain('short break');

      component.retry();
      http.expectOne(endpoint).flush({ recommendations: [recommendation], elapsedMs: 3 });

      expect(component.errorMessage).toBeNull();
      expect(component.recommendations.length).toBe(1);
    });
  });
});
