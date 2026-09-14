import { ComponentFixture, TestBed } from '@angular/core/testing';
import { configureTestBed } from '@testing';

import { RegistrationPageComponent } from './registration-page.component';

describe('RegistrationPageComponent', () => {
  let component: RegistrationPageComponent;
  let fixture: ComponentFixture<RegistrationPageComponent>;

  beforeEach(async () => {
    configureTestBed();
    await TestBed.configureTestingModule({
      imports: [RegistrationPageComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(RegistrationPageComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('requires the AI Librarian disclosure acknowledgment', () => {
    component.registerForm.patchValue({
      firstName: 'Ada',
      lastName: 'Lovelace',
      username: 'ada',
      email: 'ada@example.com',
      password: 'Secure1!'
    });

    expect(component.registerForm.invalid).toBeTrue();
    expect(component.registerForm.get('aiLibrarianDisclosureAccepted')?.hasError('required')).toBeTrue();

    component.registerForm.patchValue({ aiLibrarianDisclosureAccepted: true });

    expect(component.registerForm.valid).toBeTrue();
  });
});
