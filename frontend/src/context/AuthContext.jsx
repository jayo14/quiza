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
      // Check for Supabase session first (after Google OAuth redirect)
      try {
        const { supabase } = await import("../config/supabase");
        const { data: { session } } = await supabase.auth.getSession();
        
        if (session && session.access_token) {
          // Send Supabase token to our backend
          const response = await fetch(`${API_BASE_URL}/auth/google`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({ token: session.access_token }),
          });

          if (response.ok) {
            const data = await response.json();
            saveAuth(data.user, data.tokens.access_token, data.tokens.refresh_token);
            // Sign out of Supabase to clean up since we have our custom JWTs now
            await supabase.auth.signOut();
            setLoading(false);
            return;
          }
        }
      } catch (error) {
        console.error("Supabase session check failed:", error);
      }

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

  const refreshUser = useCallback(async () => {
    const storedToken = localStorage.getItem("access_token");
    if (!storedToken) return;
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        method: "GET",
        headers: { Authorization: `Bearer ${storedToken}` },
      });
      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        localStorage.setItem("user", JSON.stringify(userData));
      }
    } catch {
      // ignore
    }
  }, []);

  const signInWithGoogle = async () => {
    const { supabase } = await import("../config/supabase");
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: window.location.origin,
      },
    });
  };

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
    signInWithGoogle,
    signUp,
    signOut,
    refreshUser,
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
