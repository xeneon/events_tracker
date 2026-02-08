import { Link } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";

export default function Header() {
  const { user, isAuthenticated, logout } = useAuth();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
      <Link to="/" className="text-xl font-bold text-indigo-600">
        Events Tracker
      </Link>

      <nav className="flex items-center gap-4">
        <Link to="/" className="text-gray-600 hover:text-gray-900 text-sm">
          Calendar
        </Link>
        {isAuthenticated && (
          <Link to="/submit" className="text-gray-600 hover:text-gray-900 text-sm">
            Submit Event
          </Link>
        )}
        {isAuthenticated && user?.is_superuser && (
          <Link to="/admin" className="text-gray-600 hover:text-gray-900 text-sm">
            Admin
          </Link>
        )}
        {isAuthenticated ? (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{user?.email}</span>
            <button
              onClick={logout}
              className="text-sm text-red-600 hover:text-red-700"
            >
              Logout
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-2">
            <Link
              to="/login"
              className="text-sm px-3 py-1.5 text-indigo-600 hover:text-indigo-700"
            >
              Login
            </Link>
            <Link
              to="/register"
              className="text-sm px-3 py-1.5 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Register
            </Link>
          </div>
        )}
      </nav>
    </header>
  );
}
