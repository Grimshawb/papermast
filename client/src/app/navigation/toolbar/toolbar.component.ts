import { Component, EventEmitter, Input, OnDestroy, OnInit, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { AuthStore } from '../../store/auth.store';
import { Observable, Subject, takeUntil, tap } from 'rxjs';
import { User } from '../../models';
import { RouterLink, RouterLinkActive } from "@angular/router";
import { HOME_NAV_ITEM, NAVIGATION_GROUPS } from '../navigation-items';


@Component({
  selector: 'bookshelf-toolbar',
  imports: [MatIconModule, MatToolbarModule, MatButtonModule, MatSlideToggleModule, MatMenuModule,
    RouterLink, RouterLinkActive],
  standalone: true,
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.scss'
})

export class ToolbarComponent implements OnInit, OnDestroy {

  public appTitle = 'Paper Mast';
  public loggedInUser$: Observable<User>;
  public loggedInUser: User = undefined;
  public readonly homeNavItem = HOME_NAV_ITEM;
  public readonly navigationGroups = NAVIGATION_GROUPS;
  private _destroy$: Subject<void> = new Subject<void>();

  @Input()
  public isMobile: boolean = false;

  @Output()
  public onMenuClicked: EventEmitter<void> = new EventEmitter<void>();

  constructor(private _authStore: AuthStore) {}

  ngOnInit(): void {
    this.loggedInUser$ = this._authStore.select(s => s.loggedInUser)
      .pipe(takeUntil(this._destroy$), tap(l => this.loggedInUser = l));
    this.loggedInUser$.subscribe();
  }

  public menuClick(): void {
    this.onMenuClicked.emit();
  }

  public logout(): void {
    this._authStore.logout();
  }

  ngOnDestroy(): void {
    this._destroy$.next();
    this._destroy$.complete();
  }
}
