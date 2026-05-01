const SESSION_KEY = 'upserver_admin_session';

export interface AdminSession {
  token: string;
  expires_at: number;
}

export function readAdminSession(): AdminSession | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as AdminSession;
    if (!parsed || typeof parsed.token !== 'string' || typeof parsed.expires_at !== 'number') {
      return null;
    }
    if (parsed.expires_at <= Date.now() / 1000) {
      clearAdminSession();
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export function writeAdminSession(session: AdminSession): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
  } catch {
    /* localStorage may be blocked; admin still works for the current call */
  }
}

export function clearAdminSession(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(SESSION_KEY);
  } catch {
    /* nothing to do */
  }
}
