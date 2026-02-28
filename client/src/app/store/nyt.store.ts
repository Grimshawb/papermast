import { Injectable } from '@angular/core';
import { Store } from './store';
import { NytService } from '../services';
import { NytStoreState } from '../models';
import { take, tap } from 'rxjs';
import { responseToBestsellerLists } from '../utils';

@Injectable({
  providedIn: 'root'
})

export class NytStore extends Store<NytStoreState> {

  public constructor(private _nytService: NytService) {
    super({
      bestsellerLists: null
    })
  }

  public getAllBestsellerLists(): void {
    this._nytService.getAllBestSellerLists()
      .pipe(take(1))
      .subscribe(r => {
        const lists = responseToBestsellerLists(r);
        this.setState({ bestsellerLists: lists });
        console.log(lists);
      });
  }

}
