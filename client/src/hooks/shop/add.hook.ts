import { create } from "zustand";

interface Store {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export const useShopAddModal = create<Store>((set) => ({
  open: false,
  setOpen: (open: boolean) => set({ open: !open }),
}));
