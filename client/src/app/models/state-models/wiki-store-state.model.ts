import { WikiEntry } from "../wiki-entry.model";

export interface WikiStoreState {
  authorOfTheDay: WikiEntry | undefined,
}