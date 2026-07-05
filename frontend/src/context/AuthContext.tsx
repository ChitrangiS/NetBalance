import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import type { UserResponse, LoginRequest, RegisterRequest } from "../types/api";
import * as authService from "../services/authService";
import { getStoredToken, setStoredToken, clearStoredToken } from "../services/apiClient";

interface AuthContextValue {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;       // true while we're validating a stored token on mount
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // ── On mount: if a token exists in storage, validate it by calling /auth/me ──
  // This is what prevents the "flash of logged out" problem discussed in theory.
  useEffect(() => {
    async function validateStoredToken() {
      const token = getStoredToken();
      if (!token) {
        setIsLoading(false);
        return;
      }
      try {
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
      } catch {
        // Token is invalid/expired — the apiClient interceptor already
        // cleared it and will redirect; we just need to stop loading here.
        clearStoredToken();
      } finally {
        setIsLoading(false);
      }
    }
    validateStoredToken();
  }, []);

  async function login(data: LoginRequest) {
    const tokenResponse = await authService.login(data);
    setStoredToken(tokenResponse.access_token);
    const currentUser = await authService.getCurrentUser();
    setUser(currentUser);
  }

  async function register(data: RegisterRequest) {
    await authService.register(data);
    // Registration doesn't log the user in automatically (matches our
    // backend design from Step 3 — register returns 201, not a token).
    // We log them in immediately after for a smoother UX.
    await login({ email: data.email, password: data.password });
  }

  function logout() {
    clearStoredToken();
    setUser(null);
  }

  const value: AuthContextValue = {
    user,
    isAuthenticated: user !== null,
    isLoading,
    login,
    register,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook — the standard pattern for consuming a context cleanly,
// with a runtime guard against using it outside the provider.
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}