import { Component, DestroyRef, inject, Renderer2 } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { BreakpointObserver } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { SideNavComponent } from './navigation/side-nav/bookshelf-side-nav.component';
import { ToolbarComponent } from "./navigation/toolbar/toolbar.component";
import { AuthStore } from './store/auth.store';
import { OverlayContainer } from '@angular/cdk/overlay';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet, MatToolbarModule, MatSidenavModule, MatButtonModule,
    MatIconModule, SideNavComponent, ToolbarComponent],
  templateUrl: './app.component.html',
  styleUrl: './app.component.scss'
})
export class AppComponent {
  public isMobile: boolean = false;
  public mobileDrawerOpen: boolean = false;
  public themeClass = 'dark-theme';
  private readonly destroyRef = inject(DestroyRef);

  constructor(private breakpointObserver: BreakpointObserver,
              private _authStore: AuthStore,
              private overlay: OverlayContainer,
              private renderer: Renderer2) {
    this.breakpointObserver.observe(['(max-width: 767.98px)'])
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(result => {
        this.isMobile = result.matches;
        if (!this.isMobile) this.mobileDrawerOpen = false;
      });
    this._authStore.initializeAuthState();

    this.overlay.getContainerElement().classList.add(this.themeClass);
    this.renderer.addClass(document.body, this.themeClass);
  }

  public toggleMobileDrawer(): void {
    this.mobileDrawerOpen = !this.mobileDrawerOpen;
  }

  public closeMobileDrawer(): void {
    this.mobileDrawerOpen = false;
  }

  public onThemeChanged(dark: boolean): void {
    this.themeClass = dark ? 'dark-theme' : 'light-theme';

    const container = this.overlay.getContainerElement();
    container.classList.remove('light-theme', 'dark-theme');
    container.classList.add(this.themeClass);

    this.renderer.removeClass(document.body, 'light-theme');
    this.renderer.removeClass(document.body, 'dark-theme');
    this.renderer.addClass(document.body, this.themeClass);
  }
}
