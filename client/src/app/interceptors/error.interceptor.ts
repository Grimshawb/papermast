import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, EMPTY } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ToasterService } from '../services';


@Injectable()
export class ErrorInterceptor implements HttpInterceptor {

  constructor(private _toaster: ToasterService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {

        const message = error.error?.message || error.error || 'An Unexpected Error Occurred';
        this._toaster.error(message);

        // Return EMPTY so stream completes
        return EMPTY;
      })
    );
  }
}
