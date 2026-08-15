export interface NavigationItem {
  label: string;
  icon: string;
  route: string;
}

export interface NavigationGroup {
  label: string;
  icon: string;
  items: NavigationItem[];
}

export const HOME_NAV_ITEM: NavigationItem = {
  label: 'Home',
  icon: 'home',
  route: '/'
};

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: 'Discover',
    icon: 'explore',
    items: [
      { label: 'Bestsellers', icon: 'sell', route: '/bestsellers' }
    ]
  },
  {
    label: 'My Library',
    icon: 'local_library',
    items: [
      { label: 'Shelves', icon: 'menu_book', route: '/shelves' }
    ]
  }
];
