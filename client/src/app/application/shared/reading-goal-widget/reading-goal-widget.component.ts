import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ReadingGoal } from '../../../models';

@Component({
  selector: 'reading-goal-widget',
  standalone: true,
  templateUrl: './reading-goal-widget.component.html',
  styleUrl: './reading-goal-widget.component.scss'
})
export class ReadingGoalWidgetComponent {
  @Input({ required: true }) public goal!: ReadingGoal;
  @Input() public interactive = false;
  @Input() public compact = false;
  @Output() public activated = new EventEmitter<void>();

  public get percentage(): number {
    if (!this.goal.targetBookCount) return 0;
    return Math.min(100, Math.round(this.goal.completedBookCount / this.goal.targetBookCount * 100));
  }

  public activate(): void {
    if (this.interactive) this.activated.emit();
  }
}
