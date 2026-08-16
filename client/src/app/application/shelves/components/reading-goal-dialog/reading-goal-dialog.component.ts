import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { finalize, take } from 'rxjs';
import { ReadingGoal } from '../../../../models';
import { ReadingGoalsService } from '../../../../services';

@Component({
  selector: 'reading-goal-dialog',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatInputModule],
  templateUrl: './reading-goal-dialog.component.html',
  styleUrl: './reading-goal-dialog.component.scss'
})
export class ReadingGoalDialogComponent {
  public targetBookCount: number;
  public saving = false;
  public error: string | null = null;

  constructor(
    @Inject(MAT_DIALOG_DATA) public goal: ReadingGoal,
    private dialogRef: MatDialogRef<ReadingGoalDialogComponent>,
    private readingGoalsService: ReadingGoalsService
  ) {
    this.targetBookCount = goal.targetBookCount || 12;
  }

  public save(): void {
    if (!Number.isInteger(this.targetBookCount) || this.targetBookCount < 1 || this.targetBookCount > 1000) return;
    this.saving = true;
    this.error = null;
    this.readingGoalsService.save({ year: this.goal.year, targetBookCount: this.targetBookCount })
      .pipe(take(1), finalize(() => this.saving = false))
      .subscribe({
        next: goal => this.dialogRef.close(goal),
        error: () => this.error = 'We could not save your goal. Please try again.'
      });
  }
}
