// API Configuration for ARGO Backend (runtime overridable)
const STORAGE_KEY = 'api_base_url';

// Normalize a base URL: ensure protocol, remove trailing slash
export const normalizeBaseUrl = (url: string): string => {
  try {
    if (!url) return '';
    let value = String(url).trim();
    if (!/^https?:\/\//i.test(value)) {
      value = `http://${value}`; // default to http if protocol missing
    }
    // Remove trailing slash
    value = value.replace(/\/+$/, '');
    return value;
  } catch {
    return url;
  }
};

export const API_CONFIG = {
  // Default to env, fallback to localhost (can be overridden at runtime via localStorage)
  BASE_URL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000',

  // API endpoints based on your FastAPI backend
  ENDPOINTS: {
    QUERY: '/query',
    FLOATS: '/floats',
    FLOAT_DETAILS: '/float',
    UPLOAD_NETCDF: '/upload_netcdf',
    EXPORT_NETCDF: '/export_netcdf',
    EXPORT_CSV: '/export_csv',
    EXPORT_PARQUET: '/export_parquet',
    HEALTH: '/health'
  }
};

export const getApiBaseUrl = (): string => {
  try {
    if (typeof window !== 'undefined') {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      if (stored) return normalizeBaseUrl(stored);
      const host = window.location.hostname || '';
      const isLocal = /^(localhost|127\.0\.0\.1)$/i.test(host);
      const isDev = !!(import.meta as any)?.env?.DEV;
      if (!isDev && !isLocal) {
        return window.location.origin;
      }
    }
  } catch {}
  return API_CONFIG.BASE_URL;
};

export const setApiBaseUrl = (url: string) => {
  try {
    if (typeof window !== 'undefined') {
      const normalized = normalizeBaseUrl(url);
      if (!normalized) {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, normalized);
      }
    }
  } catch {}
};

// Helper function to build full API URL (supports relative base like "/api")
export const buildApiUrl = (endpoint: string, params?: Record<string, string>) => {
  const base = getApiBaseUrl();
  let full = '';
  if (/^https?:\/\//i.test(base)) {
    full = new URL(endpoint, base).toString();
  } else {
    const baseClean = (base || '').replace(/\/$/, '');
    const epClean = (endpoint || '').replace(/^\//, '');
    full = `${baseClean}/${epClean}`.replace(/^\/+/, '/');
  }
  if (params && Object.keys(params).length) {
    const u = new URL(full, typeof window !== 'undefined' ? window.location.origin : 'http://localhost');
    Object.entries(params).forEach(([k, v]) => u.searchParams.append(k, v));
    return u.toString();
  }
  return full;
};

// Fetch helper with abort/timeout support to prevent long hangs
export const fetchWithTimeout = async (
  input: RequestInfo | URL,
  init: (RequestInit & { timeoutMs?: number }) = {}
): Promise<Response> => {
  const { timeoutMs = 8000, signal, ...rest } = init;
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(new DOMException('Timeout', 'TimeoutError')), timeoutMs);
  try {
    return await fetch(input, { ...rest, signal: signal ?? controller.signal });
  } finally {
    clearTimeout(id);
  }
};

// Helper function to check if we're in development
export const isDevelopment = () => {
  return import.meta.env.DEV;
};
