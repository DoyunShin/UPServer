const UNITS = ['B', 'KB', 'MB', 'GB', 'TB'];

function pickUnitIndex(bytes: number): number {
  if (bytes < 1024) return 0;
  let value = bytes;
  let idx = 0;
  while (value >= 1024 && idx < UNITS.length - 1) {
    value /= 1024;
    idx += 1;
  }
  return idx;
}

function decimalsFor(value: number): number {
  return value >= 100 ? 0 : value >= 10 ? 1 : 2;
}

export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) return '—';
  if (bytes < 1024) return `${bytes} B`;
  const idx = pickUnitIndex(bytes);
  const value = bytes / Math.pow(1024, idx);
  return `${value.toFixed(decimalsFor(value))} ${UNITS[idx]}`;
}

export function formatBytesProgress(loaded: number, total: number): string {
  if (!Number.isFinite(total) || total <= 0) return formatBytes(loaded);
  if (total < 1024) {
    return `${Math.max(0, Math.round(loaded))} / ${Math.round(total)} B`;
  }
  const idx = pickUnitIndex(total);
  const factor = Math.pow(1024, idx);
  const t = total / factor;
  const l = Math.max(0, loaded) / factor;
  const decimals = decimalsFor(t);
  return `${l.toFixed(decimals)} / ${t.toFixed(decimals)} ${UNITS[idx]}`;
}

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

export function formatTimestamp(unixSeconds: number): string {
  if (!Number.isFinite(unixSeconds) || unixSeconds <= 0) return '—';
  const d = new Date(unixSeconds * 1000);
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function formatRelativeFromSeconds(seconds: number): string {
  if (seconds <= 0) return 'expired';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m`;
  return `${seconds}s`;
}

export function formatRelativeWords(seconds: number): string {
  if (seconds <= 0) return 'expired';
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const parts: string[] = [];
  if (days > 0) parts.push(`${days} day${days === 1 ? '' : 's'}`);
  if (hours > 0) parts.push(`${hours} hour${hours === 1 ? '' : 's'}`);
  if (parts.length === 0 && minutes > 0) parts.push(`${minutes} minute${minutes === 1 ? '' : 's'}`);
  if (parts.length === 0) parts.push(`${seconds}s`);
  return parts.join(' ');
}

export interface ExpiryInfo {
  enabled: boolean;
  expired: boolean;
  remainingSeconds: number;
  expiresAt: number;
}

export function computeExpiry(createdAt: number, deleteAfter: number, now: number = Date.now() / 1000): ExpiryInfo {
  if (deleteAfter < 0) {
    return { enabled: false, expired: false, remainingSeconds: 0, expiresAt: 0 };
  }
  const expiresAt = createdAt + deleteAfter;
  const remaining = Math.floor(expiresAt - now);
  return {
    enabled: true,
    expired: remaining <= 0,
    remainingSeconds: Math.max(0, remaining),
    expiresAt
  };
}
