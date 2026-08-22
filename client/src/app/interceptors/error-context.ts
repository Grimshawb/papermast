import { HttpContextToken } from '@angular/common/http';

/** Marks requests where a 401 is an expected logged-out result. */
export const SUPPRESS_UNAUTHORIZED_TOAST = new HttpContextToken<boolean>(() => false);
/** Leaves structured errors available to a component that renders field-level validation. */
export const HANDLE_ERROR_LOCALLY = new HttpContextToken<boolean>(() => false);
