import { Injectable } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';


@Injectable({
  providedIn: 'root'
})
export class ToasterService {

  constructor(private _snackBar: MatSnackBar) { }

  public error(msg: string): void {
    this._snackBar.open(msg, undefined, {
      data: msg,
      duration: 3000,
      horizontalPosition: 'right',
      verticalPosition: 'bottom',
      panelClass: 'error'} as MatSnackBarConfig); // TODO
  }

  public success(msg: string): void {
    this._snackBar.open(msg, undefined, {
      data: msg,
      duration: 3000,
      horizontalPosition: 'right',
      verticalPosition: 'bottom',
      panelClass: 'success'} as MatSnackBarConfig); // TODO
  }

}
