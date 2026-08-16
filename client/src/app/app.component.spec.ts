import { TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';
import { AppComponent } from './app.component';

describe('AppComponent', () => {
  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [AppComponent],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(AppComponent);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should use the dark theme by default', () => {
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance.themeClass).toBe('dark-theme');
  });
});
