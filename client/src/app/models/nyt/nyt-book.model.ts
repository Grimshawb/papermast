import { ApiBookIdentifier } from "../books-api";
import { NytBuyLink } from "./nyt-buy-link.model";

export interface NytBook {
  ageGroup: string,
  amazonProductUrl: string,
  author: string,
  bookImage: string,
  buyLinks: NytBuyLink[],
  contributor: string,
  contributorNote: string,
  createdDate: Date,
  description: string,
  isbns: ApiBookIdentifier[],
  publisher: string,
  title: string,
  weeksOnList: number
}
