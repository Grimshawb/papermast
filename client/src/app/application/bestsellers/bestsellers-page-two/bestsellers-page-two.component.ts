import { CommonModule } from '@angular/common';
import { Component, HostListener, OnDestroy, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { BestsellerCarouselCardComponent } from '../components/bestseller-carousel-card/bestseller-carousel-card.component';
import { filter, Observable, Subject, takeUntil, tap } from 'rxjs';
import { BestsellerList } from '../../../models';
import { NytStore } from '../../../store';

@Component({
  selector: 'bestsellers-page-two',
  imports: [CommonModule, MatIconModule, MatButtonModule, MatCardModule, MatProgressSpinnerModule,
    MatFormFieldModule, MatSelectModule, BestsellerCarouselCardComponent],
  templateUrl: './bestsellers-page-two.component.html',
  styleUrl: './bestsellers-page-two.component.scss'
})
export class BestsellersPageTwoComponent implements OnInit, OnDestroy {

  private readonly swipeThreshold = 50;
  private swipePointerId: number | null = null;
  private swipeListName: string | null = null;
  private swipeStartX = 0;
  private swipeStartY = 0;
  private swipeCurrentX = 0;
  private swipeCurrentY = 0;
  private wheelDistance = 0;
  private wheelGestureHandled = false;
  private wheelResetTimer: ReturnType<typeof setTimeout> | null = null;

  private destroy$: Subject<void> = new Subject<void>();
  public bestsellerLists$: Observable<BestsellerList[]>;
  public bestsellerLists: BestsellerList[];
  public selectedBestsellerList$: Observable<BestsellerList>;
  public selectedBestsellerList: BestsellerList;
  public isLoading$: Observable<boolean>;
  public error$: Observable<string>;
  public indices: {key: string, index: number, max: number}[] = [];

  constructor(private _nytStore: NytStore) {}

  ngOnInit(): void {
    this.bestsellerLists$ = this._nytStore.select(s => s.bestsellerLists)
      .pipe(filter(l => !!l),
        tap(l => {
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

    this.selectedBestsellerList$ = this._nytStore.select(s => s.selectedBestsellerList)
      .pipe(tap(l => {
         if (l) {
          this.selectedBestsellerList = l;
         }
        }), takeUntil(this.destroy$));
    this.selectedBestsellerList$.subscribe();

    this.isLoading$ = this._nytStore.select(s => s.isLoading)
      .pipe(takeUntil(this.destroy$));
    this.error$ = this._nytStore.select(s => s.error)
      .pipe(takeUntil(this.destroy$));

    // Subscribe to store state before starting the request so the initial
    // route instance observes every load transition.
    this._nytStore.getAllBestsellerLists();
  }

  public retryLoad(): void {
    this._nytStore.getAllBestsellerLists(true);
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

  public onSwipeStart(event: PointerEvent, listName: string): void {
    if (!event.isPrimary || (event.pointerType === 'mouse' && event.button !== 0)) return;

    this.swipePointerId = event.pointerId;
    this.swipeListName = listName;
    this.swipeStartX = this.swipeCurrentX = event.clientX;
    this.swipeStartY = this.swipeCurrentY = event.clientY;
  }

  @HostListener('window:pointermove', ['$event'])
  public onSwipeMove(event: PointerEvent): void {
    if (event.pointerId !== this.swipePointerId) return;

    this.swipeCurrentX = event.clientX;
    this.swipeCurrentY = event.clientY;

    const horizontalDistance = Math.abs(this.swipeCurrentX - this.swipeStartX);
    const verticalDistance = Math.abs(this.swipeCurrentY - this.swipeStartY);
    if (horizontalDistance > verticalDistance) event.preventDefault();
  }

  @HostListener('window:pointerup', ['$event'])
  public onSwipeEnd(event: PointerEvent): void {
    if (event.pointerId !== this.swipePointerId) return;

    this.swipeCurrentX = event.clientX;
    this.swipeCurrentY = event.clientY;
    const horizontalDistance = this.swipeCurrentX - this.swipeStartX;
    const verticalDistance = this.swipeCurrentY - this.swipeStartY;

    if (Math.abs(horizontalDistance) >= this.swipeThreshold &&
        Math.abs(horizontalDistance) > Math.abs(verticalDistance) &&
        this.swipeListName) {
      horizontalDistance < 0 ? this.next(this.swipeListName) : this.previous(this.swipeListName);
    }

    this.resetSwipe();
  }

  @HostListener('window:pointercancel', ['$event'])
  public onSwipeCancel(event: PointerEvent): void {
    if (event.pointerId === this.swipePointerId) this.resetSwipe();
  }

  private resetSwipe(): void {
    this.swipePointerId = null;
    this.swipeListName = null;
  }

  public onCarouselWheel(event: WheelEvent, listName: string): void {
    if (Math.abs(event.deltaX) <= Math.abs(event.deltaY)) return;

    // Keep Chrome from treating a trackpad swipe over the carousel as
    // browser back/forward navigation.
    event.preventDefault();

    if (this.wheelResetTimer) clearTimeout(this.wheelResetTimer);
    this.wheelResetTimer = setTimeout(() => {
      this.wheelDistance = 0;
      this.wheelGestureHandled = false;
      this.wheelResetTimer = null;
    }, 160);

    if (this.wheelGestureHandled) return;

    this.wheelDistance += event.deltaX;
    if (Math.abs(this.wheelDistance) < this.swipeThreshold) return;

    this.wheelDistance > 0 ? this.next(listName) : this.previous(listName);
    this.wheelGestureHandled = true;
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

  public selectListByName(listName: string): void {
    const list = this.bestsellerLists?.find(item => item.name === listName);
    if (list) this._nytStore.setSelectedBestsellerList(list);
  }

  ngOnDestroy(): void {
    if (this.wheelResetTimer) clearTimeout(this.wheelResetTimer);
    this.destroy$.next();
    this.destroy$.complete();
  }
}
