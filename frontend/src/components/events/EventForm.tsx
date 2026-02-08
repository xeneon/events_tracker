import { useState } from "react";
import { createEvent } from "@/api/events";
import { useCategories } from "@/hooks/useEvents";
import type { EventCreateData } from "@/types";

interface Props {
  onSuccess?: () => void;
}

export default function EventForm({ onSuccess }: Props) {
  const categories = useCategories();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const [form, setForm] = useState<EventCreateData>({
    title: "",
    start_date: "",
    is_all_day: true,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(false);
    setLoading(true);
    try {
      await createEvent(form);
      setSuccess(true);
      setForm({ title: "", start_date: "", is_all_day: true });
      onSuccess?.();
    } catch {
      setError("Failed to create event");
    } finally {
      setLoading(false);
    }
  };

  const update = (fields: Partial<EventCreateData>) =>
    setForm((prev) => ({ ...prev, ...fields }));

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <p className="text-red-600 text-sm">{error}</p>}
      {success && <p className="text-green-600 text-sm">Event submitted for approval!</p>}

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
        <input
          type="text"
          required
          value={form.title}
          onChange={(e) => update({ title: e.target.value })}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Start Date *</label>
          <input
            type="date"
            required
            value={form.start_date}
            onChange={(e) => update({ start_date: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
          <input
            type="date"
            value={form.end_date || ""}
            onChange={(e) => update({ end_date: e.target.value || undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
          <select
            value={form.category_id || ""}
            onChange={(e) => update({ category_id: e.target.value ? Number(e.target.value) : undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select category</option>
            {categories.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Impact (1-5)</label>
          <select
            value={form.impact_level || ""}
            onChange={(e) => update({ impact_level: e.target.value ? Number(e.target.value) : undefined })}
            className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Select impact</option>
            {[1, 2, 3, 4, 5].map((n) => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </div>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Country Code</label>
        <input
          type="text"
          maxLength={2}
          placeholder="US"
          value={form.country_code || ""}
          onChange={(e) => update({ country_code: e.target.value.toUpperCase() || undefined })}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
        <textarea
          rows={3}
          value={form.description || ""}
          onChange={(e) => update({ description: e.target.value || undefined })}
          className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-500"
        />
      </div>

      <button
        type="submit"
        disabled={loading}
        className="w-full bg-indigo-600 text-white py-2 rounded hover:bg-indigo-700 disabled:opacity-50"
      >
        {loading ? "Submitting..." : "Submit Event"}
      </button>
    </form>
  );
}
