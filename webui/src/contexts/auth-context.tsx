"use client";

import {
  type ReactNode,
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";

const TOKEN_KEY = "resume_token";
const USER_KEY = "resume_user";

interface AuthUser {
  keycloak_id: string;
  username: string;
  email: string;
  name?: string;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  loginWithKeycloak: () => void;
  loginDemo: () => void;
  setCredentials: (token: string, user: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}

function getStorage(key: string): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(key);
}
function setStorage(key: string, value: string): void {
  if (typeof window !== "undefined") localStorage.setItem(key, value);
}
function removeStorage(key: string): void {
  if (typeof window !== "undefined") localStorage.removeItem(key);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [user, setUserState] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const savedToken = getStorage(TOKEN_KEY);
    const savedUser = getStorage(USER_KEY);
    if (savedToken) setTokenState(savedToken);
    if (savedUser) {
      try {
        setUserState(JSON.parse(savedUser));
      } catch {
        removeStorage(USER_KEY);
      }
    }
    setIsLoading(false);
  }, []);

  const persist = useCallback((newToken: string | null, newUser: AuthUser | null) => {
    setTokenState(newToken);
    setUserState(newUser);
    if (newToken && newUser) {
      setStorage(TOKEN_KEY, newToken);
      setStorage(USER_KEY, JSON.stringify(newUser));
    } else {
      removeStorage(TOKEN_KEY);
      removeStorage(USER_KEY);
    }
  }, []);

  const loginDemo = useCallback(() => {
    persist("demo-token", {
      keycloak_id: "demo-user",
      username: "demo_user",
      email: "demo@resumesite.com",
      name: "Demo User",
    });
  }, [persist]);

  const loginWithKeycloak = useCallback(() => {
    const keycloakUrl = process.env.NEXT_PUBLIC_KEYCLOAK_URL || "https://keycloak.iacgenie.com";
    const realm = process.env.NEXT_PUBLIC_KEYCLOAK_REALM || "iacgenie";
    const clientId = process.env.NEXT_PUBLIC_KEYCLOAK_CLIENT_ID || "resume-platform";
    const redirectUri =
      process.env.NEXT_PUBLIC_REDIRECT_URI || `${window.location.origin}/auth/callback`;
    const state = Math.random().toString(36).substring(2) + Date.now().toString(36);
    const url = `${keycloakUrl}/realms/${realm}/protocol/openid-connect/auth?client_id=${clientId}&response_type=code&redirect_uri=${encodeURIComponent(redirectUri)}&state=${state}`;
    window.location.href = url;
  }, []);

  const logout = useCallback(() => {
    persist(null, null);
    window.location.href = "/login";
  }, [persist]);

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isLoading,
        isAuthenticated: !!token,
        loginWithKeycloak,
        loginDemo,
        setCredentials: persist,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
