import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DailyAuthorComponent } from './daily-author.component';

describe('DailyAuthorComponent', () => {
  let component: DailyAuthorComponent;
  let fixture: ComponentFixture<DailyAuthorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DailyAuthorComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(DailyAuthorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
