import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { configureTestBed } from '@testing';
import { environment } from '../../environment';

import { BooksApiService } from './books-api.service';

describe('BooksApiService', () => {
  let service: BooksApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    configureTestBed();
    TestBed.configureTestingModule({});
    service = TestBed.inject(BooksApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('loads a predefined genre and maps English books', () => {
    let titles: string[] = [];
    service.genre('horror').subscribe(books => titles = books.map(book => book.title));

    const request = http.expectOne(`${environment.BACK_END_URL}booksapi/genres/horror`);
    expect(request.request.method).toBe('GET');
    request.flush({
      items: [
        { id: 'horror-1', volumeInfo: { title: 'The Haunting', language: 'en' } },
        { id: 'other-1', volumeInfo: { title: 'Otra historia', language: 'es' } }
      ]
    });

    expect(titles).toEqual(['The Haunting']);
  });
});
