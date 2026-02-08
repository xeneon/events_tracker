import EventForm from "@/components/events/EventForm";

export default function SubmitEventPage() {
  return (
    <div className="max-w-lg mx-auto p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Submit an Event</h1>
      <div className="bg-white rounded-lg shadow p-6">
        <EventForm />
      </div>
    </div>
  );
}
