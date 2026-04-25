import { writable, type Readable } from 'svelte/store';
import { fetchInfo, type InfoData } from '$lib/api';

export interface InfoState {
  loading: boolean;
  data: InfoData | null;
  error: string | null;
}

const internal = writable<InfoState>({ loading: false, data: null, error: null });
let inflight: Promise<void> | null = null;
let loaded = false;

export const info: Readable<InfoState> = { subscribe: internal.subscribe };

export function ensureInfo(fetcher: typeof fetch = fetch): Promise<void> {
  if (loaded) return Promise.resolve();
  if (inflight) return inflight;
  internal.update((s) => ({ ...s, loading: true }));
  inflight = fetchInfo(fetcher)
    .then((data) => {
      loaded = true;
      internal.set({ loading: false, data, error: null });
    })
    .catch((err: Error) => {
      internal.set({ loading: false, data: null, error: err.message });
    })
    .finally(() => {
      inflight = null;
    });
  return inflight;
}
