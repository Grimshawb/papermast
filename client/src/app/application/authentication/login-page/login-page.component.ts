import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { ReactiveFormsModule, UntypedFormBuilder, UntypedFormGroup } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterModule } from '@angular/router';

@Component({
  selector: 'login-page',
  imports: [CommonModule, MatCardModule, MatIconModule, MatFormFieldModule,
            MatInputModule, MatButtonModule, MatCheckboxModule, ReactiveFormsModule,
            MatProgressSpinnerModule, RouterModule],
  templateUrl: './login-page.component.html',
  styleUrl: './login-page.component.scss'
})
export class LoginPageComponent implements OnInit{

  public loginForm: UntypedFormGroup;
  public hidePassword: boolean = true;
  public isLoading: boolean = false;

  constructor(private _formBuilder: UntypedFormBuilder) {}

  ngOnInit(): void {
    this.loginForm = this._formBuilder.group({
      email: null,
      password: null,
      rememberMe: null
    });
  }

  public onSubmit(): void {

  }
}
