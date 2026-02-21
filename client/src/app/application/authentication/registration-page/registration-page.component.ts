import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, Validators, ReactiveFormsModule, UntypedFormGroup } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'registration-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatFormFieldModule,
            MatInputModule, MatButtonModule, MatCardModule,
            MatIconModule, MatProgressSpinnerModule, RouterModule],
  templateUrl: './registration-page.component.html',
  styleUrls: ['./registration-page.component.scss']
})
export class RegistrationPageComponent {

  public registerForm: UntypedFormGroup;
  public hidePassword: boolean = true;
  public isLoading: boolean = false;

  constructor(private _formBuilder: FormBuilder) {
    this.registerForm = this._formBuilder.group({
      email: [null, [Validators.required, Validators.email]],
      username: [null, [Validators.required]],
      firstName: [null, [Validators.required]],
      lastName: [null, [Validators.required]],
      password: [null, [Validators.required, Validators.minLength(6)]],
      confirmPassword: [null, [Validators.required]]
    });
  }

  public onSubmit(): void {

  }
}
