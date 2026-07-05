import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from "axios";

const BASE_URL = "http://localhost:8000";

const TOKEN_STORAGE_KEY = "netbalance_token";

// ── Token storage helpers ────────────────────────────────────────────────────
// Centralized here so the rest of the app never touches localStorage directly —
// if we switch storage strategy later (Step 14: httpOnly cookies), only
// this file needs to change.

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
}

// ── Axios instance ────────────────────────────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 10000, // 10 seconds — fail fast rather than hang indefinitely
});

// ── Request interceptor: attach JWT to every outgoing request ──────────────────
apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getStoredToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle expired/invalid tokens globally ───────────────
// If ANY request comes back 401, the token is no longer valid — clear it
// and redirect to login. Without this, every component would need to
// handle 401s individually, which is exactly the duplication we want to avoid.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearStoredToken();
      // Hard redirect rather than React Router navigation — guarantees
      // all in-memory app state (including AuthContext) resets cleanly.
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;