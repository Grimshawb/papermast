export interface WikiEntry {
  title: string;
  extract: string;
  content_urls: {
    desktop: { page: string };
    mobile?: { page: string };
  };
  thumbnail?: {
    source: string;
    width: number;
    height: number;
  };
}