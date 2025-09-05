// API Configuration for ARGO Backend (runtime overridable)
const STORAGE_KEY = 'api_base_url';

export const API_CONFIG = {
  // Default to env, fallback to localhost (can be overridden at runtime via localStorage)
  BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',

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
      if (stored) return stored;
    }
  } catch {}
  return API_CONFIG.BASE_URL;
};

export const setApiBaseUrl = (url: string) => {
  try {
    if (typeof window !== 'undefined') {
      if (!url) {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, url);
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

// Helper function to check if we're in development
export const isDevelopment = () => {
  return import.meta.env.DEV;
};
