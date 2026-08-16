import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { BookListEntryComponent } from './book-list-entry.component';

describe('BookListEntryComponent', () => {
  let component: BookListEntryComponent;
  let fixture: ComponentFixture<BookListEntryComponent>;

  beforeEach(async () => {
    configureTestBed();
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
