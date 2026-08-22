import { TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { configureTestBed } from '@testing';
import { environment } from '../../environment';
import { CuratedCatalogService } from './curated-catalog.service';

describe('CuratedCatalogService', () => {
  let service: CuratedCatalogService;
  let http: HttpTestingController;

  beforeEach(() => {
    configureTestBed();
    service = TestBed.inject(CuratedCatalogService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('loads the published catalog', () => {
    let sectionCount = 0;
    service.get('horror').subscribe(catalog => sectionCount = catalog.sections.length);
    const request = http.expectOne(`${environment.BACK_END_URL}curated-catalogs/horror`);
    expect(request.request.method).toBe('GET');
    request.flush({ slug: 'horror', sections: [{ key: 'popular', title: 'Popular & Recommended', books: [] }, { key: 'upcoming', title: 'Coming Soon', books: [] }] });
    expect(sectionCount).toBe(2);
  });

  it('uploads a multipart CSV and publishes its draft', () => {
    const file = new File(['isbn,title,author'], 'horror.csv', { type: 'text/csv' });
    service.import('horror', 'popular', file).subscribe();
    const upload = http.expectOne(`${environment.BACK_END_URL}curated-catalogs/horror/imports`);
    expect(upload.request.method).toBe('POST');
    expect(upload.request.body instanceof FormData).toBeTrue();
    expect(upload.request.body.get('section')).toBe('popular');
    upload.flush({ batchId: 7, catalog: { slug: 'horror', sections: [] }, errors: [] });

    service.publish('horror', 7).subscribe();
    const publish = http.expectOne(`${environment.BACK_END_URL}curated-catalogs/horror/imports/7/publish`);
    expect(publish.request.method).toBe('POST');
    publish.flush({ slug: 'horror', sections: [] });
  });
});
