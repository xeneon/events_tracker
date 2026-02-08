import apiClient from "./client";
import type { LoginResponse, User } from "@/types";

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>(
    "/auth/login",
    new URLSearchParams({ username: email, password }),
    { headers: { "Content-Type": "application/x-www-form-urlencoded" } }
  );
  return data;
}

export async function register(email: string, password: string, displayName?: string): Promise<User> {
  const { data } = await apiClient.post<User>("/auth/register", {
    email,
    password,
    display_name: displayName,
  });
  return data;
}

export async function fetchCurrentUser(): Promise<User> {
  const { data } = await apiClient.get<User>("/users/me");
  return data;
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post("/auth/logout");
  } catch {
    // Ignore errors on logout
  }
}
