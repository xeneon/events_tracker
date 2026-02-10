import { useEffect, useState } from "react";
import { fetchCalendarEvents } from "@/api/events";

const RANKING_START = "2025-01-01";
const RANKING_END = "2027-12-31";
const DEFAULT_TOP_N = 15;
const MUSIC_RELEASES_CATEGORY = "Music Releases";
const MUSIC_RELEASES_MIN_LISTENERS = 1_000_000;

export function usePopularityThresholds() {
  const [minScoreByYearAndCat, setMinScoreByYearAndCat] = useState<Record<string, number>>({});

  useEffect(() => {
    const fetchGlobalContext = async () => {
      try {
        const allEvents = await fetchCalendarEvents(
          RANKING_START,
          RANKING_END,
          undefined,
          undefined,
          undefined
        );

        const scoresByKey: Record<string, number[]> = {};
        const categoryNameById: Record<number, string> = {};

        allEvents.forEach((ev) => {
          if (ev.category_id && ev.category_name) {
            categoryNameById[ev.category_id] = ev.category_name;
          }
          if (ev.popularity_score != null && ev.category_id) {
            const year = new Date(ev.start).getFullYear();
            const key = `${year}-${ev.category_id}`;
            if (!scoresByKey[key]) scoresByKey[key] = [];
            scoresByKey[key].push(ev.popularity_score);
          }
        });

        const thresholds: Record<string, number> = {};
        Object.keys(scoresByKey).forEach((key) => {
          const catId = parseInt(key.split("-")[1]);
          const catName = categoryNameById[catId];
          const scores = scoresByKey[key].sort((a, b) => b - a);

          if (catName === MUSIC_RELEASES_CATEGORY) {
            thresholds[key] = MUSIC_RELEASES_MIN_LISTENERS;
          } else if (scores.length >= DEFAULT_TOP_N) {
            thresholds[key] = scores[DEFAULT_TOP_N - 1];
          } else {
            thresholds[key] = 0;
          }
        });

        setMinScoreByYearAndCat(thresholds);
      } catch (e) {
        console.error("Failed to fetch global context for ranking", e);
      }
    };

    fetchGlobalContext();
  }, []);

  return minScoreByYearAndCat;
}
