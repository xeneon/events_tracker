import { useCallback, useEffect, useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import timeGridPlugin from "@fullcalendar/timegrid";
import listPlugin from "@fullcalendar/list";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventClickArg, EventSourceFuncArg } from "@fullcalendar/core";
import { fetchCalendarEvents } from "@/api/events";
import { useFilterStore } from "@/store/filterStore";
import EventDetailModal from "./EventDetailModal";
import "@/styles/calendar.css";

export default function EventCalendar() {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const { activeCategories, countryCode, searchQuery } = useFilterStore();
  const calendarRef = useRef<FullCalendar>(null);
  const [minScoreByYearAndCat, setMinScoreByYearAndCat] = useState<Record<string, number>>({});

  // 1. Pre-fetch global context to determine "Top 15" thresholds per year AND category
  useEffect(() => {
    const fetchGlobalContext = async () => {
      try {
        // Fetch a wide range (e.g., 2025-2027) to capture anticipated releases
        const allEvents = await fetchCalendarEvents(
          "2025-01-01",
          "2027-12-31",
          undefined,
          undefined,
          undefined
        );

        const scoresByKey: Record<string, number[]> = {};

        allEvents.forEach((ev) => {
          if (ev.popularity_score != null && ev.category_id) {
            const year = new Date(ev.start).getFullYear();
            const key = `${year}-${ev.category_id}`;
            if (!scoresByKey[key]) scoresByKey[key] = [];
            scoresByKey[key].push(ev.popularity_score);
          }
        });

        const thresholds: Record<string, number> = {};
        Object.keys(scoresByKey).forEach((key) => {
          const scores = scoresByKey[key].sort((a, b) => b - a);
          // Top 15 cutoff per category: Take the 15th score (index 14).
          if (scores.length >= 15) {
            thresholds[key] = scores[14];
          } else {
            thresholds[key] = 0; // Show all if fewer than 15
          }
        });

        setMinScoreByYearAndCat(thresholds);
      } catch (e) {
        console.error("Failed to fetch global context for ranking", e);
      }
    };

    fetchGlobalContext();
  }, []); // Run once on mount

  // Refetch events when filters change
  useEffect(() => {
    calendarRef.current?.getApi().refetchEvents();
  }, [activeCategories, countryCode, searchQuery, minScoreByYearAndCat]);

  const loadEvents = useCallback(
    async (fetchInfo: EventSourceFuncArg) => {
      const startDate = fetchInfo.startStr.split("T")[0];
      const endDate = fetchInfo.endStr.split("T")[0];
      try {
        const events = await fetchCalendarEvents(
          startDate,
          endDate,
          activeCategories.length > 0 ? activeCategories : undefined,
          countryCode || undefined,
          searchQuery || undefined
        );

        // Filter based on "Top 15 per Category per Year" threshold
        const filteredEvents = events.filter((ev) => {
          // Always show non-ranked events (Holidays, etc.)
          if (ev.popularity_score == null) return true;

          const year = new Date(ev.start).getFullYear();
          // Construct key using category_id. 
          // Note: If somehow category_id is missing on a scored event, we allow it (threshold 0).
          const key = ev.category_id ? `${year}-${ev.category_id}` : null;
          const threshold = key ? (minScoreByYearAndCat[key] || 0) : 0;

          return ev.popularity_score >= threshold;
        });

        return filteredEvents.map((ev) => ({
          id: ev.id,
          title: ev.title,
          start: ev.start,
          end: ev.end || undefined,
          allDay: ev.allDay,
          backgroundColor: ev.color || "#6366f1",
          borderColor: ev.color || "#6366f1",
          extendedProps: {
            category_id: ev.category_id,
            category_name: ev.category_name,
            impact_level: ev.impact_level,
            popularity_score: ev.popularity_score,
            country_code: ev.country_code,
          },
        }));
      } catch {
        return [];
      }
    },
    [activeCategories, countryCode, searchQuery, minScoreByYearAndCat]
  );

  const handleEventClick = useCallback((info: EventClickArg) => {
    setSelectedEventId(info.event.id);
  }, []);

  return (
    <>
      <FullCalendar
        ref={calendarRef}
        plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,timeGridWeek,listWeek",
        }}
        events={loadEvents}
        eventClick={handleEventClick}
        height="auto"
        nowIndicator
        dayMaxEvents={4}
        eventDisplay="block"
      />
      <EventDetailModal
        eventId={selectedEventId}
        onClose={() => setSelectedEventId(null)}
      />
    </>
  );
}
