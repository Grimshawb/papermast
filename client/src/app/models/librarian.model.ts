export interface LibrarianRecommendation {
  workKey: string;
  title: string;
  authors: string[];
  genres: string[];
  description: string;
  editionKey?: string;
  coverIds: number[];
  isbn10: string[];
  isbn13: string[];
  publicationDate?: string;
  pageCount?: number;
  reason: string;
}

export interface LibrarianResponse {
  recommendations: LibrarianRecommendation[];
  elapsedMs: number;
}
