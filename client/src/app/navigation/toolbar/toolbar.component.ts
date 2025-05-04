import { Component, EventEmitter, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import {MatSlideToggleModule} from '@angular/material/slide-toggle';

@Component({
  selector: 'bookshelf-toolbar',
  imports: [MatIconModule, MatToolbarModule, MatButtonModule, MatSlideToggleModule],
  standalone: true,
  templateUrl: './toolbar.component.html',
  styleUrl: './toolbar.component.scss'
})

export class ToolbarComponent {

  public appTitle = 'Paper Mast';
  public darkMode: boolean = false;

  @Output()
  public onCollapsedChanged: EventEmitter<boolean> = new EventEmitter<boolean>();

  @Output()
  public onDarkModeChanged: EventEmitter<boolean> = new EventEmitter<boolean>();

  public menuClick(): void {
    this.onCollapsedChanged.emit(true);
  }

  public toggleDarkMode(): void {
    this.darkMode = !this.darkMode;
    this.onDarkModeChanged.emit(this.darkMode);
  }
}
