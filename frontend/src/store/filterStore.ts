import { create } from "zustand";

interface FilterState {
  activeCategories: number[];
  searchQuery: string;
  countryCode: string;
  impactLevelMin: number | null;
  toggleCategory: (id: number, allCategoryIds: number[]) => void;
  setSearchQuery: (q: string) => void;
  setCountryCode: (code: string) => void;
  setImpactLevelMin: (level: number | null) => void;
  clearFilters: () => void;
}

export const useFilterStore = create<FilterState>((set) => ({
  activeCategories: [],
  searchQuery: "",
  countryCode: "",
  impactLevelMin: null,

  toggleCategory: (id, allCategoryIds) =>
    set((state) => {
      // When showing all (empty array), uncheck means select all except this one
      if (state.activeCategories.length === 0) {
        return { activeCategories: allCategoryIds.filter((c) => c !== id) };
      }
      const newCategories = state.activeCategories.includes(id)
        ? state.activeCategories.filter((c) => c !== id)
        : [...state.activeCategories, id];
      // If all categories are now selected, reset to empty (show all)
      if (newCategories.length === allCategoryIds.length) {
        return { activeCategories: [] };
      }
      return { activeCategories: newCategories };
    }),

  setSearchQuery: (q) => set({ searchQuery: q }),
  setCountryCode: (code) => set({ countryCode: code }),
  setImpactLevelMin: (level) => set({ impactLevelMin: level }),

  clearFilters: () =>
    set({
      activeCategories: [],
      searchQuery: "",
      countryCode: "",
      impactLevelMin: null,
    }),
}));
