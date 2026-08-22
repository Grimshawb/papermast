import { ApiBook } from './books-api';

export interface CuratedCatalogBook extends ApiBook {
  isbn13: string;
  releaseDate?: string;
  position: number;
}

export interface CuratedCatalogSection {
  key: 'popular' | 'upcoming';
  title: string;
  books: CuratedCatalogBook[];
}

export interface CuratedCatalog {
  slug: string;
  publishedAt?: string;
  sections: CuratedCatalogSection[];
}

export interface CatalogImportError {
  row: number;
  field: string;
  message: string;
}

export interface CatalogImportPreview {
  batchId: number;
  catalog: CuratedCatalog;
  errors: CatalogImportError[];
}
