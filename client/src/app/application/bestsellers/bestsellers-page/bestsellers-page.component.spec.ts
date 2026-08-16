import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { BestsellersPageComponent } from './bestsellers-page.component';

describe('BestsellersPageComponent', () => {
  let component: BestsellersPageComponent;
  let fixture: ComponentFixture<BestsellersPageComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [BestsellersPageComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BestsellersPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
