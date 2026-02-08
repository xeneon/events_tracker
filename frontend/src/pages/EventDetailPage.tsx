import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchEvent } from "@/api/events";
import type { EventData } from "@/types";
import LoadingSpinner from "@/components/common/LoadingSpinner";

export default function EventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [event, setEvent] = useState<EventData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (!id) return;
    setError(false);
    fetchEvent(id)
      .then(setEvent)
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <LoadingSpinner />;
  if (error || !event) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl text-gray-600">
          {error ? "Failed to load event" : "Event not found"}
        </h2>
        <Link to="/" className="text-indigo-600 hover:underline mt-2 inline-block">
          Back to calendar
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto p-8">
      <Link to="/" className="text-indigo-600 hover:underline text-sm mb-4 inline-block">
        &larr; Back to calendar
      </Link>
      <h1 className="text-3xl font-bold text-gray-900 mb-2">{event.title}</h1>
      {event.category && (
        <span
          className="inline-block px-2 py-1 rounded text-xs text-white mb-4"
          style={{ backgroundColor: event.category.color }}
        >
          {event.category.name}
        </span>
      )}
      <div className="bg-white rounded-lg shadow p-6 space-y-3 text-gray-600">
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
          </p>
        )}
        {event.impact_level && (
          <p>
            <span className="font-medium">Impact Level:</span> {event.impact_level}/5
          </p>
        )}
        {event.description && (
          <p className="whitespace-pre-wrap pt-3 border-t">{event.description}</p>
        )}
      </div>
    </div>
  );
}
