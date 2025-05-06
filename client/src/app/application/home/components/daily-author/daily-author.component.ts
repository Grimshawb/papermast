import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { WikiEntry } from '../../../../models';

@Component({
  selector: 'daily-author',
  imports: [CommonModule, MatCardModule],
  templateUrl: './daily-author.component.html',
  styleUrl: './daily-author.component.scss'
})
export class DailyAuthorComponent {

  @Input()
  public author: WikiEntry

  public navigateToWiki(): void {

  }
}
