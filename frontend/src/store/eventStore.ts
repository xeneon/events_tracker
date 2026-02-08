import { create } from "zustand";
import type { CalendarEvent, Category } from "@/types";

interface EventState {
  calendarEvents: CalendarEvent[];
  categories: Category[];
  loading: boolean;
  setCalendarEvents: (events: CalendarEvent[]) => void;
  setCategories: (categories: Category[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useEventStore = create<EventState>((set) => ({
  calendarEvents: [],
  categories: [],
  loading: false,
  setCalendarEvents: (calendarEvents) => set({ calendarEvents }),
  setCategories: (categories) => set({ categories }),
  setLoading: (loading) => set({ loading }),
}));
