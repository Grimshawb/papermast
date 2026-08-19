import { Component, DestroyRef, EventEmitter, inject, OnInit, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { DIRECT_NAV_ITEMS, NAVIGATION_GROUPS } from '../navigation-items';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { User } from '../../models';
import { AuthStore } from '../../store/auth.store';

@Component({
  selector: 'bookshelf-side-nav',
  imports: [MatButtonModule, MatExpansionModule, MatIconModule, RouterLink, RouterLinkActive],
  standalone: true,
  templateUrl: './bookshelf-side-nav.component.html',
  styleUrl: './bookshelf-side-nav.component.scss'
})
export class SideNavComponent implements OnInit {
  public readonly navigationGroups = NAVIGATION_GROUPS;
  public readonly directNavigationItems = DIRECT_NAV_ITEMS;
  public loggedInUser: User | undefined;
  private readonly destroyRef = inject(DestroyRef);

  constructor(private authStore: AuthStore) {}

  @Output()
  public onNavigate: EventEmitter<void> = new EventEmitter<void>();

  public ngOnInit(): void {
    this.authStore.select(state => state.loggedInUser)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(user => this.loggedInUser = user);
  }

  public navigate(): void {
    this.onNavigate.emit();
  }
}
