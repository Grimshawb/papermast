import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { SideNavComponent } from './bookshelf-side-nav.component';

describe('SideNavComponent', () => {
  let component: SideNavComponent;
  let fixture: ComponentFixture<SideNavComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [SideNavComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SideNavComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
