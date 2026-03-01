import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BestsellerCarouselCardComponent } from './bestseller-carousel-card.component';

describe('BestsellerCarouselCardComponent', () => {
  let component: BestsellerCarouselCardComponent;
  let fixture: ComponentFixture<BestsellerCarouselCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BestsellerCarouselCardComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BestsellerCarouselCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
