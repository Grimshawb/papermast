import { HttpHandler, HttpInterceptor, HttpRequest } from "@angular/common/http";
import { Injectable } from "@angular/core";
import { AuthStore } from "../store/auth.store";

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(private authStore: AuthStore) {}

  intercept(req: HttpRequest<any>, next: HttpHandler) {

    const token = this.authStore.getToken();

    if (token) {
      const cloned = req.clone({
        setHeaders: {
          Authorization: `Bearer ${token}`
        }
      });

      return next.handle(cloned);
    }

    return next.handle(req);
  }
}
