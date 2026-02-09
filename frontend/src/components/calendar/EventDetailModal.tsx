import { useEffect, useState } from "react";
import { fetchEvent } from "@/api/events";
import type { EventData } from "@/types";
import LoadingSpinner from "@/components/common/LoadingSpinner";

interface Props {
  eventId: string | null;
  onClose: () => void;
}

export default function EventDetailModal({ eventId, onClose }: Props) {
  const [event, setEvent] = useState<EventData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!eventId) return;
    // Strip recurring instance suffix (e.g., "uuid_2026-01-01" -> "uuid")
    const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const match = eventId.match(UUID_RE);
    const baseId = match ? match[0] : eventId;
    setLoading(true);
    fetchEvent(baseId)
      .then(setEvent)
      .catch(() => setEvent(null))
      .finally(() => setLoading(false));
  }, [eventId]);

  if (!eventId) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {loading ? (
          <LoadingSpinner />
        ) : event ? (
          <div className="p-6">
            <div className="flex items-start justify-between mb-4">
              <h2 className="text-xl font-semibold text-gray-900">{event.title}</h2>
              <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl">
                &times;
              </button>
            </div>

            {event.category && (
              <span
                className="inline-block px-2 py-1 rounded text-xs text-white mb-3"
                style={{ backgroundColor: event.category.color }}
              >
                {event.category.name}
              </span>
            )}

            <div className="space-y-2 text-sm text-gray-600">
              <p>
                <span className="font-medium">Date:</span> {event.start_date}
                {event.end_date && event.end_date !== event.start_date && ` - ${event.end_date}`}
              </p>
              {!event.is_all_day && event.start_time && (
                <p>
                  <span className="font-medium">Time:</span> {event.start_time}
                  {event.end_time && ` - ${event.end_time}`}
                </p>
              )}
              {event.country_code && (
                <p>
                  <span className="font-medium">Country:</span> {event.country_code}
                  {event.region && `, ${event.region}`}
                </p>
              )}
              {event.impact_level && (
                <p>
                  <span className="font-medium">Impact:</span>{" "}
                  {"*".repeat(event.impact_level)} ({event.impact_level}/5)
                </p>
              )}
              {event.description && (
                <div className="mt-3 pt-3 border-t border-gray-100">
                  <p className="font-medium mb-1">Description</p>
                  <p className="whitespace-pre-wrap">{event.description}</p>
                </div>
              )}
              {event.tags.length > 0 && (
                <div className="flex gap-1 flex-wrap mt-2">
                  {event.tags.map((tag) => (
                    <span
                      key={tag.id}
                      className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs"
                    >
                      {tag.name}
                    </span>
                  ))}
                </div>
              )}
              {event.source_url && (
                <p className="mt-2">
                  <a
                    href={event.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-indigo-600 hover:underline"
                  >
                    Source link
                  </a>
                </p>
              )}
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-gray-500">Event not found</div>
        )}
      </div>
    </div>
  );
}
