import { ApiBookIdentifier } from "./api-book-identifier.model"
import { ApiImageLink } from "./api-image-link.model"

export interface ApiBook {
  authors: string[],
  categories: string[],
  description: string,
  imageLinks: ApiImageLink,
  industryIdentifiers: ApiBookIdentifier,
  maturityRating: string,
  language: string,
  pageCount: number
  previewLink: string
  printType: string // "BOOK"
  publishedDate: Date, // "2024-07-04"
  publisher: string,
  subtitle: string,
  title: string
}
