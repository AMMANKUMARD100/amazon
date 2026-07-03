import React, { createContext, useContext, useState, useEffect } from 'react';
import api from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check login status on mount
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      setLoading(true);
      const res = await api.get('/auth/status');
      if (res.data.authenticated) {
        setUser(res.data.user);
      } else {
        setUser(null);
      }
    } catch (err) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const login = async (username, password) => {
    try {
      setError(null);
      setLoading(true);
      const res = await api.post('/auth/login', { username, password });
      setUser(res.data.user);
      return res.data.user;
    } catch (err) {
      const msg = err.response?.data?.message || 'Login failed. Please check credentials.';
      setError(msg);
      throw new Error(msg);
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);
      await api.post('/auth/logout');
    } catch (err) {
      console.error('Error during logout:', err);
    } finally {
      setUser(null);
      setLoading(false);
      window.location.href = '/login';
    }
  };

  const updateProfile = (updatedDetails) => {
    setUser(prev => prev ? { ...prev, ...updatedDetails } : null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, error, login, logout, checkAuthStatus, updateProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
