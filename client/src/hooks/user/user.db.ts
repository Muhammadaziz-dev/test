import { create } from "zustand";
import { UserType } from "@/types/user.type";

interface Store {
  user?: UserType;
  setUser: (user: UserType) => void;
}

export const useUser = create<Store>((set) => ({
  user: undefined,
  setUser: (user: UserType) => set({ user: user }),
}));
