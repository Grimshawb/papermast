import { TestBed } from '@angular/core/testing';
import { IsbnType, NytBook } from '../models';
import { RecentlyViewedService } from './recently-viewed.service';

describe('RecentlyViewedService', () => {
  let service: RecentlyViewedService;

  const book = (title: string, identifier: string): NytBook => ({
    title,
    author: 'Test Author',
    description: 'A test book',
    bookImage: 'cover.jpg',
    publisher: 'Test Press',
    isbns: [{ type: IsbnType.ISBN_13, identifier }],
    ageGroup: '',
    amazonProductUrl: '',
    buyLinks: [],
    contributor: '',
    contributorNote: '',
    createdDate: undefined,
    weeksOnList: 0
  });

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({});
    service = TestBed.inject(RecentlyViewedService);
  });

  afterEach(() => localStorage.clear());

  it('starts empty when no books have been viewed', () => {
    let books = [];
    service.books$.subscribe(value => books = value);
    expect(books.length).toBe(0);
  });

  it('places the latest book first and persists it', () => {
    service.record(book('First', '1'));
    service.record(book('Second', '2'));

    let books = [];
    service.books$.subscribe(value => books = value);
    expect(books.map(item => item.title)).toEqual(['Second', 'First']);
    expect(localStorage.getItem('papermast.recently-viewed')).toContain('Second');
  });

  it('moves a repeated book to the front without duplicating it', () => {
    service.record(book('First', '1'));
    service.record(book('Second', '2'));
    service.record(book('First', '1'));

    let books = [];
    service.books$.subscribe(value => books = value);
    expect(books.map(item => item.title)).toEqual(['First', 'Second']);
  });

  it('keeps at most twelve books', () => {
    for (let index = 0; index < 14; index++) {
      service.record(book(`Book ${index}`, `${index}`));
    }

    let books = [];
    service.books$.subscribe(value => books = value);
    expect(books.length).toBe(12);
  });
});
