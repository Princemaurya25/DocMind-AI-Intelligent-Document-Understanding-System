import React, { createContext, useContext, useState, useEffect } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Recover session on mount
  useEffect(() => {
    const recoverSession = async () => {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          const response = await api.get("/auth/me");
          setUser(response.data);
        } catch (err) {
          console.error("Session recovery failed:", err);
          logout();
        }
      }
      setLoading(false);
    };
    recoverSession();
  }, []);

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      // FastAPI login uses OAuth2 form data
      const formData = new URLSearchParams();
      formData.append("username", email);
      formData.append("password", password);

      const response = await api.post("/auth/login", formData, {
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
      });

      const { access_token, role, email: userEmail } = response.data;
      localStorage.setItem("token", access_token);
      localStorage.setItem("role", role);
      localStorage.setItem("email", userEmail);

      // Fetch user profile
      const profileResponse = await api.get("/auth/me");
      setUser(profileResponse.data);
      setLoading(false);
      return profileResponse.data;
    } catch (err) {
      setLoading(false);
      const errMsg = err.response?.data?.detail || "Invalid credentials. Please try again.";
      setError(errMsg);
      throw new Error(errMsg);
    }
  };

  const signup = async (email, password, fullName, role = "user") => {
    setLoading(true);
    setError(null);
    try {
      await api.post("/auth/signup", {
        email,
        password,
        full_name: fullName,
        role,
      });
      // Auto login after sign up
      return await login(email, password);
    } catch (err) {
      setLoading(false);
      const errMsg = err.response?.data?.detail || "Registration failed. Email might be in use.";
      setError(errMsg);
      throw new Error(errMsg);
    }
  };

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("email");
    setUser(null);
    setError(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
export default AuthContext;
