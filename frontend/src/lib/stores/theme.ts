import { writable, type Readable } from 'svelte/store';

export type Theme = 'dark' | 'light';

const STORAGE_KEY = 'theme';

function readInitial(): Theme {
  if (typeof localStorage === 'undefined') return 'dark';
  const raw = localStorage.getItem(STORAGE_KEY);
  return raw === 'light' ? 'light' : 'dark';
}

const internal = writable<Theme>(readInitial());

export const theme: Readable<Theme> = { subscribe: internal.subscribe };

export function applyTheme(next: Theme): void {
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('dark', next === 'dark');
  }
  if (typeof localStorage !== 'undefined') {
    try {
      localStorage.setItem(STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }
  internal.set(next);
}

export function toggleTheme(): void {
  const isDark =
    typeof document !== 'undefined' &&
    document.documentElement.classList.contains('dark');
  applyTheme(isDark ? 'light' : 'dark');
}
