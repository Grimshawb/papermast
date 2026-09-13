import { LibrarianRecommendation } from '../librarian.model';

export interface LibrarianStoreState {
  query: string;
  isLoading: boolean;
  hasSearched: boolean;
  errorMessage: string | null;
  recommendations: LibrarianRecommendation[];
}
