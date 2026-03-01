import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BestsellersPageTwoComponent } from './bestsellers-page-two.component';

describe('BestsellersPageTwoComponent', () => {
  let component: BestsellersPageTwoComponent;
  let fixture: ComponentFixture<BestsellersPageTwoComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BestsellersPageTwoComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BestsellersPageTwoComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
