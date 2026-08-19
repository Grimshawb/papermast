import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { AboutPageComponent } from './about-page.component';

describe('AboutPageComponent', () => {
  let component: AboutPageComponent;
  let fixture: ComponentFixture<AboutPageComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AboutPageComponent],
      providers: [provideNoopAnimations()]
    }).compileComponents();

    fixture = TestBed.createComponent(AboutPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('links to the project repository', () => {
    const link: HTMLAnchorElement = fixture.nativeElement.querySelector('a[href="https://github.com/Grimshawb/papermast"]');
    expect(link).toBeTruthy();
  });

  it('credits each external data source', () => {
    const links: HTMLAnchorElement[] = Array.from(fixture.nativeElement.querySelectorAll('.source-list a'));
    expect(links.length).toBe(4);
    expect(links.map(link => link.textContent)).toEqual([
      jasmine.stringContaining('Google Books API'),
      jasmine.stringContaining('The New York Times Books API'),
      jasmine.stringContaining('Wikipedia REST API'),
      jasmine.stringContaining('Open Library API')
    ]);
  });
});
