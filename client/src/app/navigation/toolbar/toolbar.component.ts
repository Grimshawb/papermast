import { Component, EventEmitter, OnDestroy, OnInit, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { AuthStore } from '../../store/auth.store';
import { Observable, Subject, takeUntil, tap } from 'rxjs';
import { User } from '../../models';
import { RouterLink } from "@angular/router";
import { CommonModule } from '@angular/common';

@Component({
  selector: 'bookshelf-toolbar',
  imports: [CommonModule, MatIconModule, MatToolbarModule, MatButtonModule, MatSlideToggleModule, RouterLink],
  standalone: true,
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.scss'
})

export class ToolbarComponent implements OnInit, OnDestroy {

  public appTitle = 'Paper Mast';
  public darkMode: boolean = false;
  public loggedInUser$: Observable<User>;
  public loggedInUser: User = undefined;
  private _destroy$: Subject<void> = new Subject<void>();

  @Output()
  public onCollapsedChanged: EventEmitter<boolean> = new EventEmitter<boolean>();

  @Output()
  public onDarkModeChanged: EventEmitter<boolean> = new EventEmitter<boolean>();

  constructor(private _authStore: AuthStore) {}

  ngOnInit(): void {
    this.loggedInUser$ = this._authStore.select(s => s.loggedInUser)
      .pipe(takeUntil(this._destroy$), tap(l => this.loggedInUser = l));
  }

  public menuClick(): void {
    this.onCollapsedChanged.emit(true);
  }

  public toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
    this.onDarkModeChanged.emit(this.darkMode);
  }

  ngOnDestroy(): void {
    this._destroy$.next();
    this._destroy$.complete();
  }
}
