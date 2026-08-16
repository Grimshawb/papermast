export interface BookEntry {
  entryID: number,
  source?: string,
  sourceBookID?: string,
  title: string,
  authors?: string,
  thumbnailUrl?: string,
  isbn10?: string,
  isbn13?: string,
  status: string,
  pageCount: number,
  pagesCompleted: number,
  percentCompleted: number,
  rating?: number,
  startDate?: Date,
  endDate?: Date,
  createdDate: Date,
  updatedDate: Date
}

export interface BookEntryRequest {
  source?: string,
  sourceBookID?: string,
  title: string,
  authors?: string,
  thumbnailUrl?: string,
  isbn10?: string,
  isbn13?: string,
  status: string,
  pageCount: number,
  pagesCompleted?: number,
  percentCompleted?: number
}
