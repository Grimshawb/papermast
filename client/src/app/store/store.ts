import { BehaviorSubject, distinctUntilChanged, map, Observable } from 'rxjs';

export abstract class Store<Tstate> {
  protected readonly _state$: BehaviorSubject<Tstate>;

  protected constructor(initialState: Tstate) {
    this._state$ = new BehaviorSubject<Tstate>(initialState);
  }

  get state$(): Observable<Tstate> {
    return this._state$.asObservable();
  }

  public select<K>(selector: (state: Tstate) => K): Observable<K> {
    return this._state$.asObservable().pipe(
      map(selector),
      distinctUntilChanged()
    );
  }

  protected setState(partial: Partial<Tstate>): void {
    const current = this._state$.getValue();
    this._state$.next({ ...current, ...partial });
  }

  get snapshot(): Tstate {
    return this._state$.getValue();
  }
}
