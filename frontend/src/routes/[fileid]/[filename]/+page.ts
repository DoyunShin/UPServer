import { fetchMeta, APIError, type FileMetadata } from '$lib/api';
import type { PageLoad } from './$types';

export const ssr = false;
export const prerender = false;

export interface LoadResult {
  fileid: string;
  filename: string;
  meta: FileMetadata | null;
  errorStatus: number | null;
  errorMessage: string | null;
}

export const load: PageLoad<LoadResult> = async ({ params, fetch }) => {
  const fileid = params.fileid;
  const filename = params.filename;
  try {
    const meta = await fetchMeta(fileid, filename, fetch);
    return { fileid, filename, meta, errorStatus: null, errorMessage: null };
  } catch (err) {
    const status = err instanceof APIError ? err.status : 0;
    const message = err instanceof Error ? err.message : 'Failed to load file';
    return { fileid, filename, meta: null, errorStatus: status, errorMessage: message };
  }
};
