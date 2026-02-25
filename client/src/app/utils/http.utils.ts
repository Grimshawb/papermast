import { HttpParams } from '@angular/common/http';

export function toHttpParams(obj: any): HttpParams {
  let params = new HttpParams();

  if (!obj) return params;

  Object.keys(obj).forEach(key => {
    const value = obj[key];

    if (value === null || value === undefined) return;

    if (Array.isArray(value)) {
      value.forEach(v => {
        if (v !== null && v !== undefined) {
          params = params.append(key, String(v));
        }
      });
    } else {
      params = params.set(key, String(value));
    }
  });

  return params;
}
