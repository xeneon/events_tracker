import { create } from "zustand";
import * as authApi from "@/api/auth";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
  loadUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem("token"),
  loading: !!localStorage.getItem("token"),

  login: async (email, password) => {
    const { access_token } = await authApi.login(email, password);
    localStorage.setItem("token", access_token);
    set({ token: access_token });
    const user = await authApi.fetchCurrentUser();
    set({ user });
  },

  register: async (email, password, displayName) => {
    await authApi.register(email, password, displayName);
  },

  logout: async () => {
    await authApi.logout();
    localStorage.removeItem("token");
    set({ user: null, token: null });
  },

  loadUser: async () => {
    const token = localStorage.getItem("token");
    if (!token) return;
    set({ loading: true });
    try {
      const user = await authApi.fetchCurrentUser();
      set({ user, token });
    } catch {
      localStorage.removeItem("token");
      set({ user: null, token: null });
    } finally {
      set({ loading: false });
    }
  },
}));
