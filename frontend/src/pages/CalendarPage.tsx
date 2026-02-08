import EventCalendar from "@/components/calendar/EventCalendar";
import Sidebar from "@/components/layout/Sidebar";

export default function CalendarPage() {
  return (
    <div className="flex flex-1 overflow-hidden">
      <Sidebar />
      <main className="flex-1 p-6 overflow-y-auto">
        <EventCalendar />
      </main>
    </div>
  );
}
