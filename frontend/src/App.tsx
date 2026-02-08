import { BrowserRouter, Route, Routes } from "react-router-dom";
import Header from "@/components/layout/Header";
import ProtectedRoute from "@/components/auth/ProtectedRoute";
import ErrorBoundary from "@/components/common/ErrorBoundary";
import CalendarPage from "@/pages/CalendarPage";
import EventDetailPage from "@/pages/EventDetailPage";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import AdminPage from "@/pages/AdminPage";
import SubmitEventPage from "@/pages/SubmitEventPage";

export default function App() {
  return (
    <BrowserRouter>
      <ErrorBoundary>
        <div className="flex flex-col min-h-screen">
          <Header />
          <Routes>
            <Route path="/" element={<CalendarPage />} />
            <Route path="/events/:id" element={<EventDetailPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route
              path="/submit"
              element={
                <ProtectedRoute>
                  <SubmitEventPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute requireSuperuser>
                  <AdminPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </div>
      </ErrorBoundary>
    </BrowserRouter>
  );
}
