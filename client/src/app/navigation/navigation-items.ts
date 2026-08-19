export interface NavigationItem {
  label: string;
  icon: string;
  route: string;
  requiresAuth?: boolean;
}

export interface NavigationGroup {
  label: string;
  icon: string;
  items: NavigationItem[];
  requiresAuth?: boolean;
}

export const HOME_NAV_ITEM: NavigationItem = {
  label: 'Home',
  icon: 'home',
  route: '/'
};

export const DIRECT_NAV_ITEMS: NavigationItem[] = [
  { label: 'Shelves', icon: 'menu_book', route: '/shelves', requiresAuth: true },
  { label: 'About', icon: 'info', route: '/about' }
];

export const NAVIGATION_GROUPS: NavigationGroup[] = [
  {
    label: 'Discover',
    icon: 'explore',
    items: [
      { label: 'Search', icon: 'search', route: '/search', requiresAuth: true },
      { label: 'Bestsellers', icon: 'sell', route: '/bestsellers' },
      { label: 'Browse genres', icon: 'category', route: '/genres' }
    ]
  }
];
