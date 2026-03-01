import { CommonModule } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { BestsellerCarouselCardComponent } from '../components/bestseller-carousel-card/bestseller-carousel-card.component';
import { filter, first, Observable, Subject, takeUntil, tap } from 'rxjs';
import { BestsellerList } from '../../../models';
import { NytStore } from '../../../store';

@Component({
  selector: 'bestsellers-page-two',
  imports: [CommonModule, MatIconModule, MatCardModule, BestsellerCarouselCardComponent],
  templateUrl: './bestsellers-page-two.component.html',
  styleUrl: './bestsellers-page-two.component.scss'
})
export class BestsellersPageTwoComponent implements OnInit, OnDestroy {

  private destroy$: Subject<void> = new Subject<void>();
  public bestsellerLists$: Observable<BestsellerList[]>;
  public bestsellerLists: BestsellerList[];
  public selectedBestsellerList$: Observable<BestsellerList>;
  public selectedBestsellerList: BestsellerList;
  public indices: {key: string, index: number, max: number}[] = [];

  constructor(private _nytStore: NytStore) {}

  ngOnInit(): void {
    this._nytStore.getAllBestsellerLists();
    this.bestsellerLists$ = this._nytStore.select(s => s.bestsellerLists)
      .pipe(filter(l => !!l),
        tap(l => {
          if (l) {
            this.bestsellerLists = l;
            if (!this.selectedBestsellerList) this._nytStore.setSelectedBestsellerList(l[0])
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

    this.selectedBestsellerList$ = this._nytStore.select(s => s.selectedBestsellerList)
      .pipe(tap(l => this.selectedBestsellerList = l), takeUntil(this.destroy$));
    this.selectedBestsellerList$.subscribe();
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
    if (index === (current.index - 1 < 0 ? current.max : current.index - 1)) return 'left';
    if (index === (current.index + 1 <= current.max ? current.index + 1 : 0)) return 'right';
    return 'hidden';
  }

  public getImageSource(): string {
    return document.body.classList.contains('dark-theme') ?
        'https://developer.nytimes.com/files/poweredby_nytimes_200a.png?v=1763725755000' :
        'https://developer.nytimes.com/files/poweredby_nytimes_200b.png?v=1763725748000';
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
