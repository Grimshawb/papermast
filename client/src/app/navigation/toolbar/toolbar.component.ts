import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { AuthStore } from '../../store/auth.store';
import { LibrarianStore } from '../../store/librarian.store';
import { Observable, Subject, takeUntil, tap } from 'rxjs';
import { User } from '../../models';
import { Router, RouterLink, RouterLinkActive } from "@angular/router";
import { DIRECT_NAV_ITEMS, NAVIGATION_GROUPS } from '../navigation-items';


@Component({
  selector: 'bookshelf-toolbar',
  imports: [FormsModule, MatIconModule, MatToolbarModule, MatButtonModule, MatSlideToggleModule, MatMenuModule,
    RouterLink, RouterLinkActive],
  standalone: true,
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.scss'
})

export class ToolbarComponent implements OnInit, OnDestroy {

  public appTitle = 'Paper Mast';
  public loggedInUser$: Observable<User>;
  public loggedInUser: User = undefined;
  public readonly navigationGroups = NAVIGATION_GROUPS;
  public readonly directNavigationItems = DIRECT_NAV_ITEMS;
  private _destroy$: Subject<void> = new Subject<void>();

  @Input()
  public isMobile: boolean = false;

  @Input()
  public darkMode: boolean = true;

  @Output()
  public onMenuClicked: EventEmitter<void> = new EventEmitter<void>();

  @Output()
  public onDarkModeChanged: EventEmitter<boolean> = new EventEmitter<boolean>();

  public librarianQuery = '';

  constructor(private _authStore: AuthStore, private librarianStore: LibrarianStore, private router: Router) {}

  ngOnInit(): void {
    this.loggedInUser$ = this._authStore.select(s => s.loggedInUser)
      .pipe(takeUntil(this._destroy$), tap(l => this.loggedInUser = l));
    this.loggedInUser$.subscribe();
  }

  public menuClick(): void {
    this.onMenuClicked.emit();
  }

  public toggleDarkMode(): void {
    this.onDarkModeChanged.emit(!this.darkMode);
  }

  public logout(): void {
    this._authStore.logout();
  }

  public get isLibrarianQueryValid(): boolean {
    return this.librarianStore.isQueryValid(this.librarianQuery);
  }

  public submitLibrarianSearch(): void {
    if (!this.isLibrarianQueryValid) return;
    this.librarianStore.search(this.librarianQuery);
    this.router.navigate(['/ask-the-librarian']);
  }

  public clearLibrarianQuery(): void {
    this.librarianQuery = '';
  }

  ngOnDestroy(): void {
    this._destroy$.next();
    this._destroy$.complete();
  }
}
