import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { HomePageComponent } from './home-page.component';
import { User } from '../../../models';

describe('HomePageComponent', () => {
  let component: HomePageComponent;
  let fixture: ComponentFixture<HomePageComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [HomePageComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(HomePageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('invites signed-out visitors to meet the librarian', () => {
    component.loggedInUser = undefined;
    fixture.detectChanges();

    const hero: HTMLElement = fixture.nativeElement.querySelector('.home-hero');
    expect(hero).toBeTruthy();
    expect(hero.textContent).toContain('Every reader gets a librarian.');
    expect(hero.querySelector('a[href="/register"]')).toBeTruthy();
    expect(hero.querySelector('a[href="/login"]')).toBeTruthy();
  });

  it('hides the hero once the reader is signed in', () => {
    component.loggedInUser = { email: 'reader@papermast.test' } as User;
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.home-hero')).toBeNull();
    expect(fixture.nativeElement.querySelectorAll('h1').length).toBe(1);
  });
});
