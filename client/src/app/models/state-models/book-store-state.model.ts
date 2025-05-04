import { ApiBook } from "../books-api";

export interface BookStoreState {
  selectedBook: ApiBook | undefined,
  searchResults: ApiBook[] | undefined,
  popularFiction: ApiBook[] | undefined
}
