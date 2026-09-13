import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { configureTestBed } from '@testing';
import { environment } from '../../environment';
import { LibrarianService } from './librarian.service';

describe('LibrarianService', () => {
  let service: LibrarianService;
  let http: HttpTestingController;

  beforeEach(() => {
    configureTestBed();
    service = TestBed.inject(LibrarianService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('posts the query and result count to the recommendations endpoint', () => {
    let elapsed = 0;
    service.recommend({ query: 'Something funny and weird.', resultCount: 5 })
      .subscribe(response => elapsed = response.elapsedMs);

    const request = http.expectOne(`${environment.BACK_END_URL}librarian/recommendations`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ query: 'Something funny and weird.', resultCount: 5 });

    request.flush({ recommendations: [], elapsedMs: 1234 });
    expect(elapsed).toBe(1234);
  });
});
