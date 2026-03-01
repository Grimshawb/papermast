import { Component, OnDestroy, OnInit } from '@angular/core';
import { Observable, Subject, takeUntil, tap } from 'rxjs';
import { BestsellerList } from '../../../models';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';
import { MatCardModule } from '@angular/material/card';
import { NytStore } from '../../../store';
import { BestsellerCarouselCardComponent } from '../components/bestseller-carousel-card/bestseller-carousel-card.component';

@Component({
  selector: 'bestsellers-page',
  imports: [CommonModule, MatIconModule, MatCardModule, BestsellerCarouselCardComponent],
  templateUrl: './bestsellers-page.component.html',
  styleUrl: './bestsellers-page.component.scss'
})
export class BestsellersPageComponent implements OnInit, OnDestroy {

  private destroy$: Subject<void> = new Subject<void>();
  public bestsellerLists$: Observable<BestsellerList[]>;
  public bestsellerLists: BestsellerList[];
  public indices: {key: string, index: number, max: number}[] = [];

  constructor(private _nytStore: NytStore) {}

  ngOnInit(): void {
    this._nytStore.getAllBestsellerLists();
    this.bestsellerLists$ = this._nytStore.select(s => s.bestsellerLists)
      .pipe(tap(l => { console.log('Made it'); console.log(l);
        if (l) {
          this.bestsellerLists = l;
          this.indices = this.bestsellerLists.map(bl => {
            return {
              key: bl.name,
              index: 0,
              max: bl.books.length - 1
            }
          })
        }
      }), takeUntil(this.destroy$));
    this.bestsellerLists$.subscribe();
  }

  public next(key: string): void {
    const obj = this.indices?.find(i => i.key === key);
    if (obj.index < obj.max)
      this.indices = this.indices.map(i => i.key === key ?
        {...obj, index: obj.index + 1} : i);
    else
      this.indices = this.indices.map(i => i.key === key ?
        {...obj, index: 0} : i);
  }

  public previous(key: string): void {
    const obj = this.indices?.find(i => i.key === key);
    if (obj.index > 0)
      this.indices = this.indices.map(i => i.key === key ?
        {...obj, index: obj.index - 1} : i);
    else
      this.indices = this.indices.map(i => i.key === key ?
        {...obj, index: obj.max} : i);
  }

  public currentIndex(key: string): number {
    return this.indices?.find(l => l.key === key)?.index || 0;
  }

  getPositionClass(index: number, key: string): string {
    const current = this.indices.find(i => i.key === key);
    if (index === current.index) return 'center';
    if (index === current.index - 1) return 'left';
    if (index === current.index + 1) return 'right';
    return 'hidden';
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
