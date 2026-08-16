import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { ShelvesPageComponent } from './shelves-page.component';

describe('ShelvesPageComponent', () => {
  let component: ShelvesPageComponent;
  let fixture: ComponentFixture<ShelvesPageComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [ShelvesPageComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ShelvesPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
