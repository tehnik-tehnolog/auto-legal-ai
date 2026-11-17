import type { ThemeMode } from '../types/rag';

const DEVICE_TOKEN_KEY = 'rag_legal_device_token_v1';
const THEME_STORAGE_KEY = 'rag_legal_theme_v1';

export function getStoredDeviceToken(): string {
  try {
    return window.localStorage.getItem(DEVICE_TOKEN_KEY) || '';
  } catch {
    return '';
  }
}

export function setStoredDeviceToken(token: string): void {
  try {
    if (token) {
      window.localStorage.setItem(DEVICE_TOKEN_KEY, token);
    } else {
      window.localStorage.removeItem(DEVICE_TOKEN_KEY);
    }
  } catch {
    // ignore storage quota errors
  }
}

export function getStoredTheme(): ThemeMode {
  try {
    const saved = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (saved === 'dark' || saved === 'light') return saved;
  } catch {
    // ignore
  }
  return 'light';
}

export function saveStoredTheme(theme: ThemeMode): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // ignore
  }
}

export async function apiFetch<T>(url: string, init: RequestInit = {}): Promise<T> {
  const token = getStoredDeviceToken();
  const headers = new Headers(init.headers || {});
  if (token) {
    headers.set('X-Device-Token', token);
  }
  if (!(init.body instanceof FormData) && !headers.has('Content-Type') && init.body) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(url, { ...init, headers });
  const contentType = res.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await res.json() : await res.text();

  if (!res.ok) {
    const message =
      typeof data === 'object' && data && 'error' in data
        ? String((data as { error: unknown }).error)
        : `HTTP ${res.status}`;
    throw new Error(message);
  }

  return data as T;
}
