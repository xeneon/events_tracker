import { useCallback, useEffect, useRef, useState } from "react";
import FullCalendar from "@fullcalendar/react";
import dayGridPlugin from "@fullcalendar/daygrid";
import listPlugin from "@fullcalendar/list";
import interactionPlugin from "@fullcalendar/interaction";
import type { EventClickArg, EventSourceFuncArg } from "@fullcalendar/core";
import { fetchCalendarEvents } from "@/api/events";
import { useFilterStore } from "@/store/filterStore";
import { usePopularityThresholds } from "@/hooks/usePopularityThresholds";
import type { CalendarEvent } from "@/types";
import EventDetailModal from "./EventDetailModal";
import "@/styles/calendar.css";

function eventsToTsv(events: CalendarEvent[]): string {
  const header = [
    "Title",
    "Description",
    "Category",
    "Start Date",
    "End Date",
    "Country",
    "Impact Level",
    "Popularity Score",
    "Source URL",
  ].join("\t");

  const rows = events.map((e) =>
    [
      e.title,
      `"${(e.description ?? "").replace(/"/g, '""')}"`,
      e.category_name ?? "",
      e.start.split("T")[0],
      e.end?.split("T")[0] ?? "",
      e.country_code ?? "",
      e.impact_level ?? "",
      e.popularity_score ?? "",
      e.source_url ?? "",
    ].join("\t")
  );

  return [header, ...rows].join("\n");
}

export default function EventCalendar() {
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const { activeCategories, countryCode, searchQuery } = useFilterStore();
  const calendarRef = useRef<FullCalendar>(null);
  const visibleEventsRef = useRef<CalendarEvent[]>([]);
  const minScoreByYearAndCat = usePopularityThresholds();

  // Refetch events when filters change
  useEffect(() => {
    calendarRef.current?.getApi().refetchEvents();
  }, [activeCategories, countryCode, searchQuery, minScoreByYearAndCat]);

  // Toast auto-dismiss
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(t);
  }, [toast]);

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

        visibleEventsRef.current = filteredEvents;

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
      } catch (err) {
        console.error("Failed to load calendar events", err);
        return [];
      }
    },
    [activeCategories, countryCode, searchQuery, minScoreByYearAndCat]
  );

  const handleEventClick = useCallback((info: EventClickArg) => {
    setSelectedEventId(info.event.id);
  }, []);

  function handleCopy() {
    const api = calendarRef.current?.getApi();
    const viewStart = api?.view.activeStart;
    const viewEnd = api?.view.activeEnd;
    const events = visibleEventsRef.current.filter((ev) => {
      if (!viewStart || !viewEnd) return true;
      const evDate = new Date(ev.start);
      return evDate >= viewStart && evDate < viewEnd;
    });
    if (!events.length) return;
    const tsv = eventsToTsv(events);
    const textarea = document.createElement("textarea");
    textarea.value = tsv;
    textarea.style.position = "fixed";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    setToast(`Copied ${events.length} event${events.length !== 1 ? "s" : ""} to clipboard`);
  }

  return (
    <>
      <div className="flex justify-end mb-3">
        <button
          onClick={handleCopy}
          className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
        >
          Copy Events
        </button>
      </div>
      <FullCalendar
        ref={calendarRef}
        plugins={[dayGridPlugin, listPlugin, interactionPlugin]}
        initialView="dayGridMonth"
        headerToolbar={{
          left: "prev,next today",
          center: "title",
          right: "dayGridMonth,dayGridWeek,listWeek,listMonth,listThirtyDays",
        }}
        views={{
          dayGridWeek: {
            dayMaxEvents: false,
          },
          listThirtyDays: {
            type: "list",
            duration: { days: 30 },
            buttonText: "30 Days",
          },
        }}
        buttonText={{
          month: "Month",
          week: "Week",
          listWeek: "List Week",
          listMonth: "List Month",
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
      {toast && (
        <div className="fixed bottom-6 right-6 bg-gray-800 text-white px-4 py-2 rounded shadow-lg text-sm z-50">
          {toast}
        </div>
      )}
    </>
  );
}
