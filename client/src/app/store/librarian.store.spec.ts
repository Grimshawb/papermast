import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { configureTestBed } from '@testing';
import { environment } from '../../environment';
import { LibrarianRecommendation } from '../models';
import { LibrarianStore } from './librarian.store';

describe('LibrarianStore', () => {
  let store: LibrarianStore;
  let http: HttpTestingController;

  const endpoint = `${environment.BACK_END_URL}librarian/recommendations`;

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

  beforeEach(() => {
    configureTestBed();
    store = TestBed.inject(LibrarianStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('should be created with empty initial state', () => {
    expect(store).toBeTruthy();
    expect(store.snapshot).toEqual({
      query: '',
      isLoading: false,
      hasSearched: false,
      errorMessage: null,
      recommendations: []
    });
  });

  describe('validation', () => {
    it('rejects a too-short query', () => {
      expect(store.isQueryValid('hi')).toBeFalse();
    });

    it('rejects a query over 500 characters', () => {
      expect(store.isQueryValid('a'.repeat(501))).toBeFalse();
    });

    it('accepts a trimmed 3-500 character query', () => {
      expect(store.isQueryValid('  Something funny and weird.  ')).toBeTrue();
    });

    it('does not call the API for an invalid query', () => {
      store.search('hi');
      http.expectNone(endpoint);
      expect(store.snapshot.hasSearched).toBeFalse();
    });
  });

  describe('search', () => {
    it('serializes the trimmed query and stores the response', () => {
      store.search('  Something funny and weird.  ');

      expect(store.snapshot.isLoading).toBeTrue();
      expect(store.snapshot.hasSearched).toBeTrue();

      const request = http.expectOne(endpoint);
      expect(request.request.method).toBe('POST');
      expect(request.request.body).toEqual({ query: 'Something funny and weird.', resultCount: 5 });

      request.flush({ recommendations: [recommendation], elapsedMs: 42 });

      expect(store.snapshot.isLoading).toBeFalse();
      expect(store.snapshot.errorMessage).toBeNull();
      expect(store.snapshot.recommendations).toEqual([recommendation]);
    });

    it('ignores a second search while one is already in flight', () => {
      store.search('Something funny and weird.');
      store.search('A second query entirely.');

      const pending = http.match(endpoint);
      expect(pending.length).toBe(1);
      expect(pending[0].request.body).toEqual({ query: 'Something funny and weird.', resultCount: 5 });

      pending[0].flush({ recommendations: [recommendation], elapsedMs: 5 });
      expect(store.snapshot.isLoading).toBeFalse();
    });
  });

  describe('error handling', () => {
    it('maps a 429 response to a nontechnical message', () => {
      store.search('Something funny and weird.');
      http.expectOne(endpoint).flush('Too many requests', { status: 429, statusText: 'Too Many Requests' });

      expect(store.snapshot.errorMessage).toContain('too quickly');
      expect(store.snapshot.recommendations).toEqual([]);
    });

    it('maps a 503 response to a nontechnical message', () => {
      store.search('Something funny and weird.');
      http.expectOne(endpoint).flush('Unavailable', { status: 503, statusText: 'Service Unavailable' });

      expect(store.snapshot.errorMessage).toContain('short break');
    });

    it('maps a 400 response to a nontechnical message', () => {
      store.search('Something funny and weird.');
      http.expectOne(endpoint).flush('Bad request', { status: 400, statusText: 'Bad Request' });

      expect(store.snapshot.errorMessage).toContain("couldn't quite understand");
    });

    it('retries with the last query and clears the error on success', () => {
      store.search('Something funny and weird.');
      http.expectOne(endpoint).flush('Unavailable', { status: 503, statusText: 'Service Unavailable' });

      store.retry();
      const retryRequest = http.expectOne(endpoint);
      expect(retryRequest.request.body).toEqual({ query: 'Something funny and weird.', resultCount: 5 });
      retryRequest.flush({ recommendations: [recommendation], elapsedMs: 3 });

      expect(store.snapshot.errorMessage).toBeNull();
      expect(store.snapshot.recommendations.length).toBe(1);
    });
  });
});
