import { User } from "../user.model";

export interface AuthStoreState {
  logInResponse: any,
  loggedInUser: User | undefined,
}
