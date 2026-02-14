import { User } from "../user.model";

export interface AuthStoreState {
  loggedInUser: User | undefined,
}
