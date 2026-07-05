import apiClient, { getStoredToken, setStoredToken, clearStoredToken } from "./apiClient";
import type { UserResponse } from "../types/api";

const REFRESH_TOKEN_KEY = "netbalance_refresh_token";

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setStoredRefreshToken(token: string): void {
  localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearStoredRefreshToken(): void {
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export async function register(data: {
  email: string; full_name: string; password: string;
}): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>("/v1/auth/register", data);
  return response.data;
}

export async function login(data: {
  email: string; password: string;
}): Promise<void> {
  const response = await apiClient.post<{
    access_token: string; refresh_token: string; token_type: string;
  }>("/v1/auth/login", data);
  setStoredToken(response.data.access_token);
  setStoredRefreshToken(response.data.refresh_token);
}

export async function refreshAccessToken(): Promise<boolean> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return false;

  try {
    const response = await apiClient.post<{
      access_token: string; refresh_token: string;
    }>("/v1/auth/refresh", { refresh_token: refreshToken });
    setStoredToken(response.data.access_token);
    setStoredRefreshToken(response.data.refresh_token);
    return true;
  } catch {
    clearStoredToken();
    clearStoredRefreshToken();
    return false;
  }
}

export async function getCurrentUser(): Promise<UserResponse> {
  const response = await apiClient.get<UserResponse>("/v1/auth/me");
  return response.data;
}

export async function logout(): Promise<void> {
  const refreshToken = getStoredRefreshToken();
  if (refreshToken) {
    try {
      await apiClient.post("/v1/auth/logout", { refresh_token: refreshToken });
    } catch {
      // Best-effort — clear local state regardless
    }
  }
  clearStoredToken();
  clearStoredRefreshToken();
}