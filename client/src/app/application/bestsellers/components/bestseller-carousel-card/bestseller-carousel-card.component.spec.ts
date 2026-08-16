import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { BestsellerCarouselCardComponent } from './bestseller-carousel-card.component';
import { NytBook } from '../../../../models';

describe('BestsellerCarouselCardComponent', () => {
  let component: BestsellerCarouselCardComponent;
  let fixture: ComponentFixture<BestsellerCarouselCardComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [BestsellerCarouselCardComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BestsellerCarouselCardComponent);
    component = fixture.componentInstance;
    component.book = { title: 'Test Book' } as NytBook;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
