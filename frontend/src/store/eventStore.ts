import { create } from "zustand";
import type { Category } from "@/types";

interface EventState {
  categories: Category[];
  loading: boolean;
  setCategories: (categories: Category[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useEventStore = create<EventState>((set) => ({
  categories: [],
  loading: false,
  setCategories: (categories) => set({ categories }),
  setLoading: (loading) => set({ loading }),
}));
