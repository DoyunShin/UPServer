export interface APIResponse<T> {
  status: number;
  message: string;
  data: T | null;
}

export interface InfoData {
  name: string;
  brand: string;
  info: string;
  icon: string;
  contact: string;
  webinfo: Array<[string, ...Array<[string, string]>]>;
}

export interface FileMetadata {
  id: string;
  name: string;
  mimeType: string;
  size: number;
  hidden: boolean;
  created_at: number;
  delete_after: number;
}

export interface UploadResult {
  url: string;
  fileid: string;
  filename: string;
  ownerKey: string | null;
}

export interface AdminFileItem {
  id: string;
  name: string;
  mimeType: string;
  size: number;
  hidden: boolean;
  created_at: number;
  delete_after: number;
  expires_at: number | null;
  expired: boolean;
}

export interface AdminFilesData {
  active: AdminFileItem[];
  expired: AdminFileItem[];
}

export class APIError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseEnvelope<T>(res: Response): Promise<T> {
  let body: APIResponse<T> | null = null;
  try {
    body = (await res.json()) as APIResponse<T>;
  } catch {
    throw new APIError(res.status, res.statusText || 'Invalid response');
  }
  if (!res.ok || body.status !== 200) {
    throw new APIError(body?.status ?? res.status, body?.message ?? res.statusText);
  }
  if (body.data === null || body.data === undefined) {
    throw new APIError(500, 'Missing response data');
  }
  return body.data;
}

export async function fetchInfo(fetcher: typeof fetch = fetch): Promise<InfoData> {
  const res = await fetcher('/api/info');
  return parseEnvelope<InfoData>(res);
}

export interface FetchMetaOptions {
  bearerToken?: string;
}

export async function fetchMeta(
  fileid: string,
  filename: string,
  fetcher: typeof fetch = fetch,
  options: FetchMetaOptions = {}
): Promise<FileMetadata> {
  const headers: Record<string, string> = {};
  if (options.bearerToken) headers['Authorization'] = `Bearer ${options.bearerToken}`;
  const res = await fetcher(
    `/api/v1/${encodeURIComponent(fileid)}/${encodeURIComponent(filename)}`,
    { headers }
  );
  return parseEnvelope<FileMetadata>(res);
}

export async function fetchAdminFile(
  fileid: string,
  filename: string,
  token: string
): Promise<Blob> {
  const res = await fetch(
    `/get/${encodeURIComponent(fileid)}/${encodeURIComponent(filename)}`,
    { headers: { Authorization: `Bearer ${token}` } }
  );
  if (!res.ok) {
    throw new APIError(res.status, res.statusText || `Download failed (${res.status})`);
  }
  return res.blob();
}

export async function deleteFile(
  fileid: string,
  filename: string,
  ownerKey: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const res = await fetcher(
    `/api/v1/${encodeURIComponent(fileid)}/${encodeURIComponent(filename)}`,
    {
      method: 'DELETE',
      headers: { 'X-Owner-Key': ownerKey }
    }
  );
  let body: APIResponse<null> | null = null;
  try {
    body = (await res.json()) as APIResponse<null>;
  } catch {
    /* envelope optional on some error paths */
  }
  if (!res.ok || (body && body.status !== 200)) {
    throw new APIError(body?.status ?? res.status, body?.message ?? res.statusText);
  }
}

export async function fetchAdminFiles(
  token: string,
  fetcher: typeof fetch = fetch
): Promise<AdminFilesData> {
  const res = await fetcher('/api/v1/admin/files', {
    headers: { Authorization: `Bearer ${token}` }
  });
  return parseEnvelope<AdminFilesData>(res);
}

export interface AdminLoginResult {
  token: string;
  expires_at: number;
  ttl_seconds: number;
}

export async function adminLogin(
  password: string,
  fetcher: typeof fetch = fetch
): Promise<AdminLoginResult> {
  const res = await fetcher('/api/v1/admin/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ password })
  });
  return parseEnvelope<AdminLoginResult>(res);
}

export async function adminLogout(
  token: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  await fetcher('/api/v1/admin/logout', {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` }
  });
}

export async function adminDeleteFile(
  fileid: string,
  filename: string,
  token: string,
  fetcher: typeof fetch = fetch
): Promise<void> {
  const res = await fetcher(
    `/api/v1/${encodeURIComponent(fileid)}/${encodeURIComponent(filename)}`,
    {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` }
    }
  );
  let body: APIResponse<null> | null = null;
  try {
    body = (await res.json()) as APIResponse<null>;
  } catch {
    /* envelope optional on some error paths */
  }
  if (!res.ok || (body && body.status !== 200)) {
    throw new APIError(body?.status ?? res.status, body?.message ?? res.statusText);
  }
}

export interface UploadHandle {
  promise: Promise<UploadResult>;
  abort: () => void;
}

export function uploadFile(
  file: File,
  onProgress?: (loaded: number, total: number) => void
): UploadHandle {
  const xhr = new XMLHttpRequest();
  const promise = new Promise<UploadResult>((resolve, reject) => {
    const url = `/${encodeURIComponent(file.name)}`;
    xhr.open('PUT', url, true);
    xhr.upload.onprogress = (ev) => {
      if (onProgress && ev.lengthComputable) {
        onProgress(ev.loaded, ev.total);
      }
    };
    xhr.onload = () => {
      if (xhr.status === 200) {
        const text = (xhr.responseText || '').trim();
        const ownerKey = xhr.getResponseHeader('X-Owner-Key');
        try {
          const u = new URL(text, window.location.origin);
          const parts = u.pathname.split('/').filter(Boolean);
          if (parts.length >= 2) {
            const fileid = decodeURIComponent(parts[0]);
            const filename = decodeURIComponent(parts.slice(1).join('/'));
            resolve({ url: text, fileid, filename, ownerKey });
            return;
          }
        } catch {
          /* fall through */
        }
        reject(new APIError(500, 'Could not parse upload response'));
      } else {
        let message = `Upload failed (${xhr.status})`;
        try {
          const body = JSON.parse(xhr.responseText) as APIResponse<unknown>;
          if (body && body.message) message = body.message;
        } catch {
          if (xhr.responseText) message = xhr.responseText;
        }
        reject(new APIError(xhr.status || 0, message));
      }
    };
    xhr.onerror = () => reject(new APIError(0, 'Network error'));
    xhr.onabort = () => reject(new APIError(0, 'Upload cancelled'));
    xhr.send(file);
  });
  return { promise, abort: () => xhr.abort() };
}
