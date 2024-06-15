import { create } from "zustand";

interface Store {
  open: boolean;
  setOpen: (open: boolean) => void;

  id?: number;
  setId: (id: number) => void;
}

export const useDeleteShop = create<Store>((set) => ({
  open: false,
  setOpen: (open: boolean) => set({ open: !open }),

  setId: (id: number) => set({ id: id }),
}));
