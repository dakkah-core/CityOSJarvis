import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router';
import { ErrorBoundary } from './components/ErrorBoundary';
import App from './App';
import { initApiBase } from './lib/api';
import { initAnalytics } from './lib/analytics';
import './index.css';

declare global {
  interface Window {
    __openJarvisAuthFetchInstalled?: boolean;
  }
}

function getStoredJarvisSettings(): { apiUrl?: string; apiKey?: string } {
  try {
    const raw = localStorage.getItem('openjarvis-settings');
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function parseRequestUrl(input: RequestInfo | URL): URL | null {
  try {
    const rawUrl = input instanceof Request ? input.url : input.toString();
    return new URL(rawUrl, window.location.origin);
  } catch {
    return null;
  }
}

function isJarvisApiUrl(target: URL, apiUrl?: string): boolean {
  const isApiPath = target.pathname.startsWith('/v1/') || target.pathname.startsWith('/api/');
  if (!isApiPath) return false;

  try {
    const base = apiUrl ? new URL(apiUrl, window.location.origin) : new URL(window.location.origin);
    return target.origin === base.origin;
  } catch {
    return target.origin === window.location.origin;
  }
}

function installJarvisApiAuth(): void {
  if (window.__openJarvisAuthFetchInstalled) return;
  const nativeFetch = window.fetch.bind(window);

  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const settings = getStoredJarvisSettings();
    const apiKey = settings.apiKey?.trim();
    const target = parseRequestUrl(input);

    if (!apiKey || !target || !isJarvisApiUrl(target, settings.apiUrl)) {
      return nativeFetch(input, init);
    }

    const headers = new Headers(
      init?.headers ?? (input instanceof Request ? input.headers : undefined),
    );
    if (!headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${apiKey}`);
    }

    if (input instanceof Request) {
      return nativeFetch(new Request(input, { ...init, headers }));
    }
    return nativeFetch(input, { ...init, headers });
  };

  window.__openJarvisAuthFetchInstalled = true;
}

function applyTheme() {
  try {
    const raw = localStorage.getItem('openjarvis-settings');
    const settings = raw ? JSON.parse(raw) : {};
    const theme = settings.theme || 'system';
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else if (theme === 'light') {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
    }
  } catch { /* use system default */ }
}

applyTheme();
installJarvisApiAuth();

// Fetch the API base URL from the Tauri backend before rendering.
// This ensures JARVIS_PORT is defined in one place (the Rust backend).
// In non-Tauri environments this is a no-op.
initApiBase().finally(() => {
  // Kick off analytics init in the background — it's never awaited so
  // a slow/failed identity fetch never delays UI render.
  void initAnalytics();

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <ErrorBoundary>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ErrorBoundary>
    </StrictMode>,
  );
});
