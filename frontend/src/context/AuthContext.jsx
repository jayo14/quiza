import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { API_BASE_URL } from "../config/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const savedUser = localStorage.getItem("user");
      return savedUser ? JSON.parse(savedUser) : null;
    } catch {
      return null;
    }
  });

  const [token, setToken] = useState(() => localStorage.getItem("access_token") || null);
  const [loading, setLoading] = useState(true);

  const saveAuth = (userData, accessToken, refreshToken) => {
    setUser(userData);
    setToken(accessToken);
    if (accessToken) localStorage.setItem("access_token", accessToken);
    if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
    if (userData) localStorage.setItem("user", JSON.stringify(userData));
  };

  const signOut = useCallback(() => {
    setUser(null);
    setToken(null);
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
  }, []);

  useEffect(() => {
    const checkAuth = async () => {
      const storedToken = localStorage.getItem("access_token");
      if (!storedToken) {
        setUser(null);
        setToken(null);
        setLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
          method: "GET",
          headers: {
            Authorization: `Bearer ${storedToken}`,
          },
        });

        if (!response.ok) {
          throw new Error("Session expired");
        }

        const userData = await response.json();
        setUser(userData);
        setToken(storedToken);
        localStorage.setItem("user", JSON.stringify(userData));
      } catch (error) {
        console.error("Auth check failed:", error);
        signOut();
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [signOut]);

  const signIn = async (email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/signin`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorMsg =
        typeof data.detail === "string"
          ? data.detail
          : data.detail?.[0]?.msg || "Sign in failed";
      throw new Error(errorMsg);
    }

    saveAuth(data.user, data.tokens.access_token, data.tokens.refresh_token);
    return data;
  };

  const signUp = async (name, email, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/signup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ name, email, password }),
    });

    const data = await response.json();

    if (!response.ok) {
      const errorMsg =
        typeof data.detail === "string"
          ? data.detail
          : data.detail?.[0]?.msg || "Sign up failed";
      throw new Error(errorMsg);
    }

    saveAuth(data.user, data.tokens.access_token, data.tokens.refresh_token);
    return data;
  };

  const value = {
    user,
    token,
    isAuthenticated: !!token && !!user,
    loading,
    signIn,
    signUp,
    signOut,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
