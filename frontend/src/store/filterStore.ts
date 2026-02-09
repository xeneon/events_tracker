import { create } from "zustand";

interface FilterState {
  activeCategories: number[];
  searchQuery: string;
  countryCode: string;
  toggleCategory: (id: number, allCategoryIds: number[]) => void;
  setSearchQuery: (q: string) => void;
  setCountryCode: (code: string) => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  activeCategories: [],
  searchQuery: "",
  countryCode: "US",

  toggleCategory: (id, allCategoryIds) =>
    set((state) => {
      // If none selected (implies all are selected), and we toggle one...
      // The Sidebar likely renders them all as checked.
      // So toggling `id` means we want to UNCHECK `id`, so we select ALL others.
      if (state.activeCategories.length === 0) {
        return { activeCategories: allCategoryIds.filter((c) => c !== id) };
      }

      const isSelected = state.activeCategories.includes(id);
      let newCategories: number[];

      if (isSelected) {
        newCategories = state.activeCategories.filter((c) => c !== id);
      } else {
        newCategories = [...state.activeCategories, id];
      }

      // If all are selected manually, reset to empty (semantic "All")
      if (newCategories.length === allCategoryIds.length) {
        return { activeCategories: [] };
      }

      return { activeCategories: newCategories };
    }),

  setSearchQuery: (q) => set({ searchQuery: q }),
  setCountryCode: (code) => set({ countryCode: code }),

  clearFilters: () =>
    set({
      activeCategories: [],
      searchQuery: "",
      countryCode: "US",
    }),
}));
