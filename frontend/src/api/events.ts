import apiClient from "./client";
import type { CalendarEvent, EventCreateData, EventData, PaginatedEvents } from "@/types";

export async function fetchCalendarEvents(
  startDate: string,
  endDate: string,
  categoryIds?: number[],
  countryCode?: string,
  search?: string
): Promise<CalendarEvent[]> {
  const params: Record<string, string | string[]> = {
    start_date: startDate,
    end_date: endDate,
  };
  if (categoryIds?.length) {
    params.category_ids = categoryIds.map(String);
  }
  if (countryCode) {
    params.country_code = countryCode;
  }
  if (search) {
    params.search = search;
  }
  const { data } = await apiClient.get<CalendarEvent[]>("/events/calendar", { params });
  return data;
}

export async function fetchEvents(params?: Record<string, unknown>): Promise<PaginatedEvents> {
  const { data } = await apiClient.get<PaginatedEvents>("/events", { params });
  return data;
}

export async function fetchEvent(id: string): Promise<EventData> {
  const { data } = await apiClient.get<EventData>(`/events/${id}`);
  return data;
}

export async function createEvent(eventData: EventCreateData): Promise<EventData> {
  const { data } = await apiClient.post<EventData>("/events", eventData);
  return data;
}

export async function updateEvent(id: string, eventData: Partial<EventCreateData>): Promise<EventData> {
  const { data } = await apiClient.put<EventData>(`/events/${id}`, eventData);
  return data;
}

export async function deleteEvent(id: string): Promise<void> {
  await apiClient.delete(`/events/${id}`);
}

export async function approveEvent(id: string): Promise<EventData> {
  const { data } = await apiClient.post<EventData>(`/events/${id}/approve`);
  return data;
}
