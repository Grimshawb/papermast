import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BookListEntryComponent } from './book-list-entry.component';

describe('BookListEntryComponent', () => {
  let component: BookListEntryComponent;
  let fixture: ComponentFixture<BookListEntryComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BookListEntryComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BookListEntryComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
