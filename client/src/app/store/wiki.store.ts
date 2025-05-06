import { Injectable } from '@angular/core';
import { BehaviorSubject, filter, take } from 'rxjs';
import { WikiService } from '../services/wiki.service';
import { WikiStoreState } from '../models/state-models/wiki-store-state.model';
import { Store } from './store';

@Injectable({
  providedIn: 'root'
})

export class WikiStore extends Store<WikiStoreState> {

  public constructor(private _wikiService: WikiService) {
    super({
      authorOfTheDay: undefined
    })
  }


  public getAuthorOfTheDay(name: string): void {
    this._wikiService.getAuthorSummary(name)
      .pipe(take(1))
      .subscribe(res => this.setState({ authorOfTheDay: res }))
  }
}
