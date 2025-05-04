export interface BookEntry {
  entryID: number,
  userID: number,
  isbn10?: string,
  isbn13?: string,
  rating?: number,
  userReview?: string,
  userInternalReview?: string,
  startDate?: Date,
  endDate?: Date
}
