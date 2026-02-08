import { useEffect } from "react";
import apiClient from "@/api/client";
import { useEventStore } from "@/store/eventStore";
import type { Category } from "@/types";

export function useCategories() {
  const { categories, setCategories } = useEventStore();

  useEffect(() => {
    if (categories.length > 0) return;
    apiClient.get<Category[]>("/categories").then(({ data }) => setCategories(data));
  }, [categories.length, setCategories]);

  return categories;
}
