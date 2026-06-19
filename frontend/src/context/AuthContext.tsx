"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
} from "react";
import { useRouter, usePathname } from "next/navigation";
import { apiClient } from "@/lib/api";

export type UserRole = "Admin" | "Reviewer";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  organization?: string | null;
  display_name?: string | null;
  avatar_url?: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  isAdmin: boolean;
  isReviewer: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await apiClient.get("/auth/me");
      setUser(response.data);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } catch (err: any) {
      setUser(null);
      // Don't set error for 401s - that's expected when not logged in
      if (err.response?.status !== 401) {
        setError(err.response?.data?.detail || "Failed to fetch user");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiClient.post("/auth/logout");
    } catch {
      // Ignore errors during logout
    }
    setUser(null);
    router.push("/login");
  }, [router]);

  // Fetch user on mount (only on admin routes)
  useEffect(() => {
    if (pathname?.startsWith("/admin")) {
      refresh();
    } else {
      setLoading(false);
    }
  }, [pathname, refresh]);

  const isAdmin = user?.role === "Admin";
  const isReviewer = user?.role === "Reviewer";

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        logout,
        refresh,
        isAdmin,
        isReviewer,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
