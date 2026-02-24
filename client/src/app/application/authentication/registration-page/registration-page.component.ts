import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, Validators, ReactiveFormsModule, UntypedFormGroup } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../services/auth.service';
import { take, finalize } from 'rxjs/operators';
import { ToasterService } from '../../../services/toaster.service';
import { fadeAnimation } from '../../../constants';

@Component({
  selector: 'registration-page',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatFormFieldModule,
            MatInputModule, MatButtonModule, MatCardModule,
            MatIconModule, MatProgressSpinnerModule, RouterModule],
  templateUrl: './registration-page.component.html',
  styleUrls: ['./registration-page.component.scss'],
  animations: [fadeAnimation]
})

export class RegistrationPageComponent {

  public registerForm: UntypedFormGroup;
  public hidePassword: boolean = true;
  public isLoading: boolean = false;

  constructor(private _formBuilder: FormBuilder,
              private _authService: AuthService,
              private _toaster: ToasterService,
              private _router: Router) {
    this.registerForm = this._formBuilder.group({
      email: [null, [Validators.required, Validators.email]],
      username: [null, [Validators.required]],
      firstName: [null, [Validators.required]],
      lastName: [null, [Validators.required]],
      password: [null, [Validators.required, Validators.minLength(8), Validators.maxLength(64),
                        Validators.pattern(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z\d]).+$/)]]
    });
  }

  public onSubmit(): void {
    this.registerForm.markAllAsTouched();
    if (!this.registerForm.valid) {return;}
    this.isLoading = true;
    this._authService.register(this.registerForm.value)
      .pipe(take(1),
            finalize(() => {
              this.isLoading = false;
            }))
      .subscribe(u => {
        if (u) {
          this._toaster.success('Registration Successful! You Can Now Log In With Your Credentials');
          this._router.navigate(['/login']);
        }
      });
  }
}
