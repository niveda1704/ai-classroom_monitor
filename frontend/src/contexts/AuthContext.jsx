import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import api from '../services/api';

const AuthContext = createContext(null);

// Get cached user from localStorage
const getCachedUser = () => {
  try {
    const cached = localStorage.getItem('auth_user');
    return cached ? JSON.parse(cached) : null;
  } catch {
    return null;
  }
};

export function AuthProvider({ children }) {
  // Initialize with cached user for instant loading
  const [user, setUser] = useState(getCachedUser);
  const [loading, setLoading] = useState(!getCachedUser());
  const [error, setError] = useState(null);

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('auth_token');
    if (!token) {
      setLoading(false);
      setUser(null);
      return;
    }

    // If we have cached user, don't block rendering
    if (getCachedUser()) {
      setLoading(false);
      // Verify in background
      api.getProfile().then(response => {
        setUser(response.data.user);
        localStorage.setItem('auth_user', JSON.stringify(response.data.user));
      }).catch(() => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        setUser(null);
      });
      return;
    }

    try {
      const response = await api.getProfile();
      setUser(response.data.user);
      localStorage.setItem('auth_user', JSON.stringify(response.data.user));
    } catch (err) {
      console.error('Auth check failed:', err);
      localStorage.removeItem('auth_token');
      localStorage.removeItem('auth_user');
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email, password) => {
    setError(null);
    try {
      const response = await api.login(email, password);
      setUser(response.data.user);
      localStorage.setItem('auth_user', JSON.stringify(response.data.user));
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const register = async (userData) => {
    setError(null);
    try {
      const response = await api.register(userData);
      setUser(response.data.user);
      localStorage.setItem('auth_user', JSON.stringify(response.data.user));
      return response;
    } catch (err) {
      setError(err.message);
      throw err;
    }
  };

  const logout = async () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setUser(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    isAuthenticated: !!user,
    isFaculty: user?.role === 'faculty',
    isAdmin: user?.role === 'admin',
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
