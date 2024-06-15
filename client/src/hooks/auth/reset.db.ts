import { create } from "zustand";

interface Store {
  phone_number: string;
  setPhone_number: (phone_number: string) => void;
}

export const useReset = create<Store>((set) => ({
  phone_number: "",
  setPhone_number: (phone_number: string) =>
    set({ phone_number: phone_number }),
}));
