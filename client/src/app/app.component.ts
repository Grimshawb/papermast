import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { BreakpointObserver, Breakpoints, LayoutModule } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { SideNavComponent } from './navigation/side-nav/bookshelf-side-nav.component';
import { ToolbarComponent } from "./navigation/toolbar/toolbar.component";
import { AuthStore } from './store/auth.store';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, MatToolbarModule, MatSidenavModule, MatButtonModule,
    MatIconModule, LayoutModule, SideNavComponent, ToolbarComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  public collapsed: boolean = false;
  public isMobile: boolean = false;
  public themeClass = 'dark-theme';

  constructor(private breakpointObserver: BreakpointObserver,
              private _authStore: AuthStore) {
    this.breakpointObserver.observe([Breakpoints.Handset])
      .subscribe(result => {
        this.isMobile = result.matches;
        if (this.isMobile) this.collapsed = true;
      });
    this._authStore.initializeAuthState();
  }

  public toggleCollapsed(): void {
    this.collapsed = !this.collapsed;
  }

  public onThemeChanged(dark: boolean): void {
    if (dark)
      this.themeClass = 'dark-theme';
    else
      this.themeClass = 'light-theme';
  }
}
