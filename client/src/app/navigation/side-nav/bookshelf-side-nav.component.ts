import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { NAVIGATION_GROUPS } from '../navigation-items';

@Component({
  selector: 'bookshelf-side-nav',
  imports: [MatButtonModule, MatExpansionModule, MatIconModule, RouterLink, RouterLinkActive],
  standalone: true,
  templateUrl: './bookshelf-side-nav.component.html',
  styleUrl: './bookshelf-side-nav.component.scss'
})
export class SideNavComponent {
  public readonly navigationGroups = NAVIGATION_GROUPS;

  @Input()
  public darkMode: boolean = true;

  @Output()
  public onDarkModeChanged: EventEmitter<boolean> = new EventEmitter<boolean>();

  @Output()
  public onNavigate: EventEmitter<void> = new EventEmitter<void>();

  public toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
    this.onDarkModeChanged.emit(this.darkMode);
  }

  public navigate(): void {
    this.onNavigate.emit();
  }
}
