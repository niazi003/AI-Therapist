// Auth hook for managing user state
import { useState, useEffect, useCallback } from 'react';
import { ApiError, authApi } from '../api/client';
import type { User, Token } from '../types';

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export function useAuth() {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const checkAuth = useCallback(async () => {
    const token = localStorage.getItem('token');
    if (!token) {
      setState({ user: null, isAuthenticated: false, isLoading: false, error: null });
      return;
    }
    try {
      const user = await authApi.me();
      setState({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err) {
      const isInvalidToken =
        err instanceof ApiError && (err.status === 401 || err.status === 403);
      if (isInvalidToken) {
        localStorage.removeItem('token');
      }
      setState({
        user: null,
        isAuthenticated: false,
        isLoading: false,
        error: isInvalidToken
          ? null
          : err instanceof Error
            ? err.message
            : 'Could not verify your session. Please try again.',
      });
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const login = async (email: string, password: string): Promise<void> => {
    setState(s => ({ ...s, isLoading: true, error: null }));
    try {
      const tokenData: Token = await authApi.login(email, password);
      localStorage.setItem('token', tokenData.access_token);
      const user = await authApi.me();
      setState({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Login failed';
      setState(s => ({ ...s, isLoading: false, error: message }));
      throw err; // Let LoginPage know so it can block onLoginSuccess
    }
  };

  const register = async (email: string, password: string, fullName?: string): Promise<void> => {
    setState(s => ({ ...s, isLoading: true, error: null }));
    try {
      await authApi.register(email, password, fullName);
    } catch (err) {
      // Registration itself failed (e.g. duplicate email)
      const message = err instanceof Error ? err.message : 'Registration failed';
      setState(s => ({ ...s, isLoading: false, error: message }));
      throw err;
    }
    // Auto-login after successful registration
    // login() manages its own error state, so we just await it
    await login(email, password);
  };

  const logout = () => {
    localStorage.removeItem('token');
    setState({ user: null, isAuthenticated: false, isLoading: false, error: null });
  };

  return {
    ...state,
    login,
    register,
    logout,
    checkAuth,
  };
}