"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { User, LoginPayload, RegisterPayload, AuthResponse } from "@/types/auth";
import { api } from "./api";
import { getQueryClient } from "./query-client";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (payload: LoginPayload) => Promise<User>;
  register: (payload: RegisterPayload) => Promise<User>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let isMounted = true;

    api.get<User>("/api/v1/auth/me/")
      .then((data) => {
        if (isMounted) {
          setUser(data);
          setLoading(false);
        }
      })
      .catch(() => {
        if (isMounted) {
          setUser(null);
          setLoading(false);
        }
      });

    // Listen for auth-expired event dispatched by api.ts when refresh fails
    const handleAuthExpired = () => {
      setUser(null);
      setLoading(false);
      const queryClient = getQueryClient();
      queryClient.clear();
    };

    window.addEventListener("handoff-auth-expired", handleAuthExpired);
    return () => {
      isMounted = false;
      window.removeEventListener("handoff-auth-expired", handleAuthExpired);
    };
  }, []);

  const login = async (payload: LoginPayload): Promise<User> => {
    const queryClient = getQueryClient();
    queryClient.clear();
    const res = await api.post<AuthResponse>("/api/v1/auth/login/", payload);
    setUser(res.user);
    return res.user;
  };

  const register = async (payload: RegisterPayload): Promise<User> => {
    const queryClient = getQueryClient();
    queryClient.clear();
    const res = await api.post<AuthResponse>("/api/v1/auth/register/", payload);
    setUser(res.user);
    return res.user;
  };

  const logout = async (): Promise<void> => {
    try {
      await api.post("/api/v1/auth/logout/");
    } catch (err) {
      console.error("Logout request failed:", err);
    } finally {
      setUser(null);
      const queryClient = getQueryClient();
      queryClient.clear();
      router.push("/login");
    }
  };

  const refreshUser = async (): Promise<void> => {
    try {
      const data = await api.get<User>("/api/v1/auth/me/");
      setUser(data);
    } catch {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        login,
        register,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
