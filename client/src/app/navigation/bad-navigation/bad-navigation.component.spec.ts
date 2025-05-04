import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BadNavigationComponent } from './bad-navigation.component';

describe('BadNavigationComponent', () => {
  let component: BadNavigationComponent;
  let fixture: ComponentFixture<BadNavigationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BadNavigationComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(BadNavigationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
