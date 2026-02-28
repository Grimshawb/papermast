import { NytBook } from "./nyt-book.model";

export interface BestsellerList {
  bestsellersDate: Date,
  name: string,
  books: NytBook[]
}
