import { Injectable } from '@angular/core';
import { Store } from './store';
import { NytService } from '../services';
import { BestsellerList, NytStoreState } from '../models';
import { defaultIfEmpty, take } from 'rxjs';
import { responseToBestsellerLists } from '../utils';

@Injectable({
  providedIn: 'root'
})

export class NytStore extends Store<NytStoreState> {

  public constructor(private _nytService: NytService) {
    super({
      bestsellerLists: null,
      selectedBestsellerList: null,
      isLoading: false,
      error: null
    })
  }

  public getAllBestsellerLists(forceReload: boolean = false): void {
    if (this.snapshot.isLoading) return;

    if (!forceReload && this.snapshot.bestsellerLists?.length) {
      if (!this.snapshot.selectedBestsellerList) {
        this.setState({ selectedBestsellerList: this.snapshot.bestsellerLists[0] });
      }
      return;
    }

    this.setState({ isLoading: true, error: null });

    this._nytService.getAllBestSellerLists()
      // The global error interceptor completes failed requests with no value.
      .pipe(take(1), defaultIfEmpty(null))
      .subscribe(r => {
        if (!r) {
          this.setState({
            isLoading: false,
            error: 'We could not load the bestseller lists. Please try again.'
          });
          return;
        }

        const lists = responseToBestsellerLists(r);
        if (!lists.length) {
          this.setState({
            bestsellerLists: [],
            selectedBestsellerList: null,
            isLoading: false,
            error: 'No bestseller lists are currently available.'
          });
          return;
        }

        this.setState({
          bestsellerLists: lists,
          selectedBestsellerList: lists[0],
          isLoading: false,
          error: null
        });
      });
  }

  public setSelectedBestsellerList(list: BestsellerList): void {
    this.setState({ selectedBestsellerList: list });
  }

}
