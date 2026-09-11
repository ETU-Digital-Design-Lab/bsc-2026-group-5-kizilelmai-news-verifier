/**
 * useAuth — Kimlik doğrulama state ve işlemlerini yöneten özel hook.
 */
import { useState, useCallback } from 'react';
import * as api from '../services/api';

const SESSION_KEY = 'kizilelma_auth';

function loadSession() {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function saveSession(data) {
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(data));
}

function clearSession() {
  sessionStorage.removeItem(SESSION_KEY);
}

export function useAuth() {
  const [auth, setAuth] = useState(() => loadSession());

  const isLoggedIn = !!auth?.token;
  const isAdmin    = auth?.role === 'admin';
  const token      = auth?.token || null;
  const userName   = auth ? `${auth.first_name || ''} ${auth.last_name || ''}`.trim() : '';

  const loginHandler = useCallback(async (email, password) => {
    const data = await api.login(email, password);
    if (data.access_token) {
      const session = {
        token:      data.access_token,
        role:       data.role,
        first_name: data.first_name,
        last_name:  data.last_name,
      };
      saveSession(session);
      setAuth(session);
      return { ok: true, role: data.role };
    }
    return { ok: false, error: data.detail || 'Giriş başarısız.' };
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setAuth(null);
  }, []);

  return { auth, token, isLoggedIn, isAdmin, userName, login: loginHandler, logout };
}
