const STORAGE_KEY = 'upserver.ownerKeys';

type KeyMap = Record<string, string>;

function readMap(): KeyMap {
  if (typeof localStorage === 'undefined') return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (parsed && typeof parsed === 'object') return parsed as KeyMap;
  } catch {
    /* ignore corrupt store */
  }
  return {};
}

function writeMap(map: KeyMap): void {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(map));
  } catch {
    /* quota or privacy mode — silent */
  }
}

export function getOwnerKey(fileid: string): string | null {
  const map = readMap();
  return map[fileid] ?? null;
}

export function setOwnerKey(fileid: string, key: string): void {
  const map = readMap();
  map[fileid] = key;
  writeMap(map);
}

export function clearOwnerKey(fileid: string): void {
  const map = readMap();
  if (fileid in map) {
    delete map[fileid];
    writeMap(map);
  }
}
