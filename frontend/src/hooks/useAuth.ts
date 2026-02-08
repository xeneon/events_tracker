import { useEffect } from "react";
import { useAuthStore } from "@/store/authStore";

export function useAuth() {
  const { user, token, loading, loadUser, login, logout, register } = useAuthStore();

  useEffect(() => {
    if (token && !user) {
      loadUser();
    }
  }, [token, user, loadUser]);

  return { user, token, loading, isAuthenticated: !!token, login, logout, register };
}
