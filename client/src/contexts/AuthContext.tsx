import React, { createContext, useContext, useEffect, useState } from "react";
import { API_BASE_URL } from "@/const";

interface User {
  username: string;
  full_name?: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem("automata_token"));
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (token) {
      verifyToken(token);
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const verifyToken = async (authToken: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });

      if (response.ok) {
        const userData = await response.json();
        setUser(userData);
        setIsLoading(false);
      } else {
        // Token expirado o inválido
        logout();
      }
    } catch (error) {
      console.error("Error verificando token:", error);
      setIsLoading(false);
    }
  };

  const login = async (authToken: string) => {
    localStorage.setItem("automata_token", authToken);
    setToken(authToken);
    await verifyToken(authToken);
  };

  const logout = () => {
    localStorage.removeItem("automata_token");
    setToken(null);
    setUser(null);
    setIsLoading(false);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
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
