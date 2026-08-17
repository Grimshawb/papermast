import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';
import { MatDialog } from '@angular/material/dialog';

import { BookListEntryComponent } from './book-list-entry.component';
import { ApiBook } from '../../../../models';
import { BestsellerBookDialogComponent } from '../../../bestsellers/components/bestseller-book-dialog/bestseller-book-dialog.component';

describe('BookListEntryComponent', () => {
  let component: BookListEntryComponent;
  let fixture: ComponentFixture<BookListEntryComponent>;
  let dialog: jasmine.SpyObj<MatDialog>;

  beforeEach(async () => {
    dialog = jasmine.createSpyObj<MatDialog>('MatDialog', ['open']);
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [BookListEntryComponent],
      providers: [{ provide: MatDialog, useValue: dialog }]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BookListEntryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('opens the bestseller-style dialog with Google Books metadata', () => {
    component.book = {
      id: 'google-book-id',
      title: 'Test Book',
      authors: ['Test Author'],
      description: 'Description',
      imageLinks: { thumbnail: 'cover.jpg' },
      industryIdentifiers: [],
      pageCount: 321,
      publisher: 'Test Publisher'
    } as ApiBook;

    component.showDetails();

    expect(dialog.open).toHaveBeenCalledWith(BestsellerBookDialogComponent, jasmine.objectContaining({
      data: jasmine.objectContaining({
        source: 'google-books',
        sourceBookID: 'google-book-id',
        pageCount: 321
      })
    }));
  });
});
