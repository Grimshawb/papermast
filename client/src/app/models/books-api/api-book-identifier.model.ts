import { IsbnType } from './isbn-type.enum'

export interface ApiBookIdentifier {
  type: IsbnType,
  identifier: string
}
