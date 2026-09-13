import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpTestingController } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { configureTestBed } from '@testing';
import { AuthStore } from '../../store/auth.store';
import { User } from '../../models';

import { ToolbarComponent } from './toolbar.component';

describe('ToolbarComponent', () => {
  let component: ToolbarComponent;
  let fixture: ComponentFixture<ToolbarComponent>;
  let http: HttpTestingController;
  let authStore: AuthStore;
  let router: Router;

  const loggedInUser = { userID: 1, email: 'brad@example.com' } as User;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [ToolbarComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ToolbarComponent);
    component = fixture.componentInstance;
    http = TestBed.inject(HttpTestingController);
    authStore = TestBed.inject(AuthStore);
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('header search visibility', () => {
    it('is hidden when the user is logged out', () => {
      fixture.detectChanges();
      const field = fixture.nativeElement.querySelector('.header-search');
      expect(field).toBeNull();
    });

    it('is hidden on mobile even when logged in', () => {
      component.isMobile = true;
      (authStore as any).setState({ loggedInUser });
      fixture.detectChanges();

      const field = fixture.nativeElement.querySelector('.header-search');
      expect(field).toBeNull();
    });

    it('is shown on desktop when logged in', () => {
      component.isMobile = false;
      (authStore as any).setState({ loggedInUser });
      fixture.detectChanges();

      const field = fixture.nativeElement.querySelector('.header-search');
      expect(field).toBeTruthy();
    });
  });

  describe('submitLibrarianSearch', () => {
    it('does nothing for an invalid query', () => {
      component.librarianQuery = 'hi';
      component.submitLibrarianSearch();
      http.expectNone(() => true);
    });

    it('searches and navigates to the results page without clearing the field', () => {
      spyOn(router, 'navigate');
      component.librarianQuery = 'Something funny and weird.';

      component.submitLibrarianSearch();

      const request = http.expectOne(req => req.url.endsWith('librarian/recommendations'));
      expect(request.request.body).toEqual({ query: 'Something funny and weird.', resultCount: 5 });
      request.flush({ recommendations: [], elapsedMs: 1 });

      expect(component.librarianQuery).toBe('Something funny and weird.');
      expect(router.navigate).toHaveBeenCalledWith(['/ask-the-librarian']);
    });
  });

  describe('clear button', () => {
    beforeEach(() => {
      component.isMobile = false;
      (authStore as any).setState({ loggedInUser });
    });

    it('is present but visually hidden when the field is empty, so the field does not resize', () => {
      component.librarianQuery = '';
      fixture.detectChanges();

      const clearButton = fixture.nativeElement.querySelector('.header-search-clear') as HTMLButtonElement;
      expect(clearButton).toBeTruthy();
      expect(clearButton.classList).toContain('header-search-clear--hidden');
    });

    it('becomes visible once there is text and clears the field on click', () => {
      component.librarianQuery = 'Something funny and weird.';
      fixture.detectChanges();

      const clearButton = fixture.nativeElement.querySelector('.header-search-clear') as HTMLButtonElement;
      expect(clearButton.classList).not.toContain('header-search-clear--hidden');

      clearButton.click();
      expect(component.librarianQuery).toBe('');
    });

    it('clearLibrarianQuery empties the field directly', () => {
      component.librarianQuery = 'Something funny and weird.';
      component.clearLibrarianQuery();
      expect(component.librarianQuery).toBe('');
    });
  });
});
