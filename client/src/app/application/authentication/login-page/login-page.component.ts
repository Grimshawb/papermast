import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ReactiveFormsModule, UntypedFormBuilder, UntypedFormGroup, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router, RouterModule } from '@angular/router';
import { AuthStore } from '../../../store/auth.store';
import { filter, take } from 'rxjs';
import { ToasterService } from '../../../services';
import { fadeAnimation } from '../../../constants';

@Component({
  selector: 'login-page',
  imports: [CommonModule, MatCardModule, MatIconModule, MatFormFieldModule,
            MatInputModule, MatButtonModule, MatCheckboxModule, ReactiveFormsModule,
            MatProgressSpinnerModule, RouterModule],
  templateUrl: './login-page.component.html',
  styleUrl: './login-page.component.scss',
  animations: [fadeAnimation]
})
export class LoginPageComponent implements OnInit{

  public loginForm: UntypedFormGroup;
  public hidePassword: boolean = true;
  public isLoading: boolean = false;

  constructor(private _formBuilder: UntypedFormBuilder,
              private _authStore: AuthStore,
              private _toaster: ToasterService,
              private _router: Router) {}

  ngOnInit(): void {
    this.loginForm = this._formBuilder.group({
      email: [null, Validators.required],
      password: [null, Validators.required],
    });
  }

  public onSubmit(): void {
      this.loginForm.markAllAsTouched();
      if (!this.loginForm.valid) return;
      this.isLoading = true;
      const res = this._authStore.select(s => s.logInResponse)
        .pipe(filter(r => !!r), take(1));
      res.subscribe(r => {
        this.isLoading = false
        this._toaster.success('Success! You Are Now Logged In');
        this._authStore.setLoginResponse(null);
        this._router.navigate(['']);
      })
      this._authStore.login(this.loginForm.value);
    }
}
