import { HttpContextToken } from '@angular/common/http';

/** Marks requests where a 401 is an expected logged-out result. */
export const SUPPRESS_UNAUTHORIZED_TOAST = new HttpContextToken<boolean>(() => false);
