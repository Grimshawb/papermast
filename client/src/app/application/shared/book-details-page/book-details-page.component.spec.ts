import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { BookDetailsPageComponent } from './book-details-page.component';

describe('BookDetailsPageComponent', () => {
  let component: BookDetailsPageComponent;
  let fixture: ComponentFixture<BookDetailsPageComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [BookDetailsPageComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BookDetailsPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
