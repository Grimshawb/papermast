import { BreakpointObserver, Breakpoints, LayoutModule } from '@angular/cdk/layout';
import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSidenavModule } from '@angular/material/sidenav';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'bookshelf-side-nav',
  imports: [CommonModule, MatSidenavModule, MatButtonModule, MatIconModule, LayoutModule, RouterModule],
  standalone: true,
  templateUrl: './bookshelf-side-nav.component.html',
  styleUrl: './bookshelf-side-nav.component.scss'
})
export class SideNavComponent {

  public isMobile: boolean = false;

  @Input()
  public set isCollapsed(c: boolean) {
    this.collapsed = c;
  }
  public collapsed: boolean = true;

  constructor(private breakpointObserver: BreakpointObserver) {
    this.breakpointObserver.observe([Breakpoints.Handset])
      .subscribe(result => {
        this.isMobile = result.matches;
        if (this.isMobile) this.collapsed = true;
      });
  }
}
