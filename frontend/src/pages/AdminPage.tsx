import { useEffect, useState } from "react";
import apiClient from "@/api/client";
import { approveEvent } from "@/api/events";
import type { DataSource, EventData } from "@/types";

export default function AdminPage() {
  const [pendingEvents, setPendingEvents] = useState<EventData[]>([]);
  const [dataSources, setDataSources] = useState<DataSource[]>([]);
  const [syncing, setSyncing] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setError(null);
      const [eventsRes, sourcesRes] = await Promise.all([
        apiClient.get<EventData[]>("/admin/events/pending"),
        apiClient.get<DataSource[]>("/admin/data-sources"),
      ]);
      setPendingEvents(eventsRes.data);
      setDataSources(sourcesRes.data);
    } catch {
      setError("Failed to load admin data.");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (id: string) => {
    try {
      await approveEvent(id);
      setPendingEvents((prev) => prev.filter((e) => e.id !== id));
    } catch {
      setError("Failed to approve event.");
    }
  };

  const handleSync = async (sourceId: number) => {
    setSyncing(sourceId);
    try {
      setError(null);
      await apiClient.post(`/admin/data-sources/${sourceId}/sync`);
      await loadData();
    } catch {
      setError("Sync failed.");
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Admin Dashboard</h1>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      <section className="mb-8">
        <h2 className="text-lg font-semibold text-gray-800 mb-4">
          Pending Events ({pendingEvents.length})
        </h2>
        {pendingEvents.length === 0 ? (
          <p className="text-gray-500">No pending events</p>
        ) : (
          <div className="space-y-2">
            {pendingEvents.map((event) => (
              <div
                key={event.id}
                className="bg-white border rounded-lg p-4 flex items-center justify-between"
              >
                <div>
                  <p className="font-medium text-gray-900">{event.title}</p>
                  <p className="text-sm text-gray-500">
                    {event.start_date} &middot; {event.category?.name || "Uncategorized"}
                  </p>
                </div>
                <button
                  onClick={() => handleApprove(event.id)}
                  className="px-3 py-1 bg-green-600 text-white text-sm rounded hover:bg-green-700"
                >
                  Approve
                </button>
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <h2 className="text-lg font-semibold text-gray-800 mb-4">Data Sources</h2>
        <div className="space-y-2">
          {dataSources.map((source) => (
            <div
              key={source.id}
              className="bg-white border rounded-lg p-4 flex items-center justify-between"
            >
              <div>
                <p className="font-medium text-gray-900">{source.name}</p>
                <p className="text-sm text-gray-500">
                  {source.source_type} &middot;{" "}
                  {source.last_synced_at
                    ? `Last sync: ${new Date(source.last_synced_at).toLocaleString()}`
                    : "Never synced"}
                </p>
              </div>
              <button
                onClick={() => handleSync(source.id)}
                disabled={syncing === source.id || !source.is_active}
                className="px-3 py-1 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
              >
                {syncing === source.id ? "Syncing..." : "Sync Now"}
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
