import { BestsellerList } from "../nyt";

export interface NytStoreState {
  bestsellerLists: BestsellerList[],
  selectedBestsellerList: BestsellerList,
  isLoading: boolean,
  error: string
}
