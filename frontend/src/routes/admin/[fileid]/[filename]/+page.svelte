<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { page } from '$app/stores';
  import Preview from '$lib/components/Preview.svelte';
  import { ICONS, kindFromName } from '$lib/utils/kind';
  import {
    formatBytes,
    formatTimestamp,
    formatRelativeFromSeconds,
    formatRelativeWords,
    computeExpiry
  } from '$lib/utils/format';
  import {
    APIError,
    adminDeleteFile,
    adminUpdateFileExpiry,
    fetchAdminFile,
    fetchMeta,
    type FileMetadata
  } from '$lib/api';
  import { readAdminSession, clearAdminSession } from '$lib/stores/admin-session';

  type Status = 'idle' | 'loading' | 'ready' | 'unauthenticated' | 'notfound' | 'error';

  let status: Status = 'idle';
  let errorMessage = '';
  let toastMessage = '';
  let meta: FileMetadata | null = null;

  let host = '';
  let cliCopied = false;
  let confirmingDelete = false;
  let deleting = false;
  let downloading = false;
  let lastLoadKey: string | null = null;

  let previewUrl = '';
  let previewLoading = false;
  let previewSkippedReason: 'too-large' | 'load-failed' | '' = '';

  let editingExpiry = false;
  let savingExpiry = false;
  let expiryNeverChecked = false;
  let expiryDateValue = '';

  // Cap blob-backed previews so a single oversized expired file cannot
  // exhaust the tab's memory just from rendering its preview.
  const PREVIEW_SIZE_CAP = 50 * 1024 * 1024;

  $: fileid = $page.params.fileid ?? '';
  $: filename = $page.params.filename ?? '';
  $: kind = meta ? kindFromName(meta.name, meta.mimeType) : 'file';

  $: if (fileid && filename) {
    const key = `${fileid}/${filename}`;
    if (key !== lastLoadKey) {
      lastLoadKey = key;
      meta = null;
      confirmingDelete = false;
      load();
    }
  }

  $: encodedPath = `${encodeURIComponent(fileid)}/${encodeURIComponent(filename)}`;
  $: publicDownloadUrl = `/get/${encodedPath}`;
  $: curlCommand = host
    ? `curl -O -H "Authorization: Bearer <admin-token>" ${host}/get/${encodedPath}`
    : `curl -O -H "Authorization: Bearer <admin-token>" /get/${encodedPath}`;

  $: expiry = meta
    ? computeExpiry(meta.created_at, meta.delete_after)
    : { enabled: false, expired: false, remainingSeconds: 0, expiresAt: 0 };

  $: expiresLabel = !expiry.enabled
    ? 'Never'
    : expiry.expired
      ? 'Expired'
      : `in ${formatRelativeFromSeconds(expiry.remainingSeconds)}`;

  $: expiryWords = !expiry.enabled
    ? 'Never expires'
    : expiry.expired
      ? 'Link expired'
      : `Link expires in ${formatRelativeWords(expiry.remainingSeconds)}`;

  function revokePreviewUrl(): void {
    if (previewUrl && previewUrl.startsWith('blob:')) {
      URL.revokeObjectURL(previewUrl);
    }
    previewUrl = '';
  }

  async function setupPreview(): Promise<void> {
    revokePreviewUrl();
    previewSkippedReason = '';
    if (!meta) return;
    const exp = computeExpiry(meta.created_at, meta.delete_after);
    if (!exp.expired) {
      previewUrl = publicDownloadUrl;
      return;
    }
    if (meta.size > PREVIEW_SIZE_CAP) {
      previewSkippedReason = 'too-large';
      return;
    }
    const session = readAdminSession();
    if (!session) {
      previewSkippedReason = 'load-failed';
      return;
    }
    const requestedKey = `${fileid}/${filename}`;
    previewLoading = true;
    try {
      const blob = await fetchAdminFile(fileid, filename, session.token);
      // Drop the result if the user navigated to a different file while
      // the blob was downloading — otherwise we'd attach a preview from
      // the previous file to the current page.
      if (lastLoadKey !== requestedKey) {
        return;
      }
      previewUrl = URL.createObjectURL(blob);
    } catch {
      if (lastLoadKey === requestedKey) {
        previewSkippedReason = 'load-failed';
      }
    } finally {
      if (lastLoadKey === requestedKey) {
        previewLoading = false;
      }
    }
  }

  async function load(): Promise<void> {
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    const requestedKey = `${fileid}/${filename}`;
    status = 'loading';
    errorMessage = '';
    revokePreviewUrl();
    previewLoading = false;
    previewSkippedReason = '';
    try {
      const result = await fetchMeta(fileid, filename, fetch, { bearerToken: session.token });
      // Drop the result if the user navigated to a different file while
      // metadata was in flight — otherwise we'd render stale meta on the
      // current route or pair it with the wrong preview URL.
      if (lastLoadKey !== requestedKey) {
        return;
      }
      meta = result;
      status = 'ready';
      setupPreview();
    } catch (err) {
      if (lastLoadKey !== requestedKey) {
        return;
      }
      if (err instanceof APIError) {
        if (err.status === 401) {
          clearAdminSession();
          status = 'unauthenticated';
          errorMessage = 'Session expired. Please sign in again.';
          return;
        }
        if (err.status === 404) {
          status = 'notfound';
          return;
        }
        errorMessage = err.message || `Request failed (${err.status})`;
      } else if (err instanceof Error) {
        errorMessage = err.message;
      } else {
        errorMessage = 'Unknown error';
      }
      status = 'error';
    }
  }

  async function downloadFile(): Promise<void> {
    if (!meta) return;
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    downloading = true;
    try {
      const blob = await fetchAdminFile(fileid, filename, session.token);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = meta.name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      if (err instanceof APIError && err.status === 401) {
        clearAdminSession();
        status = 'unauthenticated';
        errorMessage = 'Session expired. Please sign in again.';
      } else {
        toastMessage = err instanceof Error ? err.message : 'Download failed';
        setTimeout(() => (toastMessage = ''), 3000);
      }
    } finally {
      downloading = false;
    }
  }

  async function copyCli(): Promise<void> {
    if (!curlCommand) return;
    try {
      await navigator.clipboard.writeText(curlCommand);
      cliCopied = true;
      setTimeout(() => (cliCopied = false), 1400);
    } catch {
      /* clipboard unavailable */
    }
  }

  async function confirmRemove(): Promise<void> {
    if (!meta || deleting) return;
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    deleting = true;
    try {
      await adminDeleteFile(fileid, filename, session.token);
      toastMessage = 'File removed';
      setTimeout(() => goto('/admin'), 600);
      return;
    } catch (err) {
      if (err instanceof APIError && err.status === 401) {
        clearAdminSession();
        status = 'unauthenticated';
        errorMessage = 'Session expired. Please sign in again.';
      } else if (err instanceof APIError && err.status === 404) {
        toastMessage = 'File no longer exists';
        setTimeout(() => goto('/admin'), 600);
        return;
      } else {
        toastMessage = err instanceof Error ? err.message : 'Remove failed';
        setTimeout(() => (toastMessage = ''), 3000);
      }
    }
    deleting = false;
    confirmingDelete = false;
  }

  function pad2(n: number): string {
    return n < 10 ? `0${n}` : String(n);
  }

  function unixToDatetimeLocal(unix: number): string {
    const d = new Date(unix * 1000);
    return (
      `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T` +
      `${pad2(d.getHours())}:${pad2(d.getMinutes())}`
    );
  }

  function startEditExpiry(): void {
    if (!meta) return;
    const exp = computeExpiry(meta.created_at, meta.delete_after);
    expiryNeverChecked = !exp.enabled;
    const seedUnix = exp.enabled && !exp.expired ? exp.expiresAt : Date.now() / 1000 + 7 * 86400;
    expiryDateValue = unixToDatetimeLocal(seedUnix);
    editingExpiry = true;
  }

  function cancelEditExpiry(): void {
    editingExpiry = false;
    savingExpiry = false;
  }

  async function saveExpiry(): Promise<void> {
    if (!meta || savingExpiry) return;
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    let deleteAfter: number;
    if (expiryNeverChecked) {
      deleteAfter = -1;
    } else {
      const picked = new Date(expiryDateValue);
      const pickedUnix = picked.getTime() / 1000;
      if (!Number.isFinite(pickedUnix)) {
        toastMessage = 'Pick a valid date and time.';
        setTimeout(() => (toastMessage = ''), 3000);
        return;
      }
      deleteAfter = Math.max(0, Math.floor(pickedUnix - meta.created_at));
    }
    savingExpiry = true;
    try {
      const updated = await adminUpdateFileExpiry(
        fileid,
        filename,
        deleteAfter,
        session.token
      );
      meta = updated;
      editingExpiry = false;
      toastMessage = 'Expiry updated';
      setTimeout(() => (toastMessage = ''), 2000);
    } catch (err) {
      if (err instanceof APIError && err.status === 401) {
        clearAdminSession();
        status = 'unauthenticated';
        errorMessage = 'Session expired. Please sign in again.';
      } else if (err instanceof APIError && err.status === 404) {
        toastMessage = 'File no longer exists';
        setTimeout(() => goto('/admin'), 600);
        return;
      } else {
        toastMessage = err instanceof Error ? err.message : 'Update failed';
        setTimeout(() => (toastMessage = ''), 3000);
      }
    } finally {
      savingExpiry = false;
    }
  }

  onMount(() => {
    host = `${window.location.protocol}//${window.location.host}`;
  });

  onDestroy(() => {
    revokePreviewUrl();
  });
</script>

<svelte:head>
  <title>{filename} · Admin</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<div class="wrap-narrow">
  <div class="topbar">
    <a class="back" href="/admin">← Back to admin</a>
    <span class="badge">Admin</span>
  </div>

  {#if status === 'idle' || status === 'loading'}
    <div class="dl-card">
      <div class="preview">
        <div class="preview-empty"><div class="hint">Loading…</div></div>
      </div>
    </div>
  {:else if status === 'unauthenticated'}
    <div class="dl-card">
      <div class="preview">
        <div class="preview-empty">
          <div class="big-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round">{@html ICONS.file}</svg
            >
          </div>
          <div class="hint">{errorMessage || 'Sign in required.'}</div>
          <a class="btn-primary" href="/admin">Go to admin sign-in</a>
        </div>
      </div>
    </div>
  {:else if status === 'notfound'}
    <div class="dl-card">
      <div class="preview">
        <div class="preview-empty">
          <div class="big-icon">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="1.5"
              stroke-linecap="round"
              stroke-linejoin="round">{@html ICONS.file}</svg
            >
          </div>
          <span class="ext-badge">404</span>
          <div class="hint">No file with id {fileid} and name {filename}.</div>
          <a class="btn-secondary" href="/admin">Back to admin</a>
        </div>
      </div>
    </div>
  {:else if status === 'error'}
    <div class="dl-card">
      <div class="preview">
        <div class="preview-empty">
          <div class="hint error">{errorMessage}</div>
          <button class="btn-secondary" type="button" on:click={load}>Retry</button>
        </div>
      </div>
    </div>
  {:else if meta}
    <div class="dl-card">
      <div class="file-head">
        <div class="file-icon-sm">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.75"
            stroke-linecap="round"
            stroke-linejoin="round">{@html ICONS[kind]}</svg
          >
        </div>
        <div class="file-head-text">
          <h1 class="file-name">{meta.name}</h1>
          <div class="file-meta">
            <span>{formatBytes(meta.size)}</span>
            <span class="sep">·</span>
            <span>{meta.mimeType || 'unknown'}</span>
            {#if expiry.expired}
              <span class="sep">·</span>
              <span class="pill-expired">expired</span>
            {/if}
          </div>
        </div>
        <div class="head-actions">
          {#if confirmingDelete}
            <button class="btn-danger" type="button" disabled={deleting} on:click={confirmRemove}>
              {deleting ? 'Removing…' : 'Confirm remove'}
            </button>
            <button
              class="btn-secondary"
              type="button"
              disabled={deleting}
              on:click={() => (confirmingDelete = false)}
            >
              Cancel
            </button>
          {:else}
            <button
              class="btn-secondary"
              type="button"
              on:click={() => (confirmingDelete = true)}
              aria-label="Remove file"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                stroke-linejoin="round"
                ><polyline points="3 6 5 6 21 6" /><path
                  d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"
                /><path d="M10 11v6" /><path d="M14 11v6" /><path
                  d="M9 6V4a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"
                /></svg
              >
              Remove
            </button>
          {/if}
          <button
            class="btn-primary"
            type="button"
            on:click={downloadFile}
            disabled={downloading}
            aria-label="Download file"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              ><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline
                points="7 10 12 15 17 10"
              /><line x1="12" y1="15" x2="12" y2="3" /></svg
            >
            {downloading ? 'Downloading…' : 'Download'}
          </button>
        </div>
      </div>

      {#if previewLoading}
        <div class="preview">
          <div class="preview-empty"><div class="hint">Loading preview…</div></div>
        </div>
      {:else if previewSkippedReason === 'too-large'}
        <div class="preview">
          <div class="preview-empty">
            <div class="big-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round">{@html ICONS[kind]}</svg
              >
            </div>
            <span class="ext-badge">{expiry.expired ? 'expired' : 'large'}</span>
            <div class="hint">
              File is larger than {formatBytes(PREVIEW_SIZE_CAP)}. Use Download above.
            </div>
          </div>
        </div>
      {:else if previewSkippedReason === 'load-failed'}
        <div class="preview">
          <div class="preview-empty">
            <div class="big-icon">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="1.5"
                stroke-linecap="round"
                stroke-linejoin="round">{@html ICONS[kind]}</svg
              >
            </div>
            <span class="ext-badge">unavailable</span>
            <div class="hint">Could not load preview. Use Download above.</div>
          </div>
        </div>
      {:else if previewUrl}
        <Preview
          filename={meta.name}
          mimeType={meta.mimeType}
          downloadUrl={previewUrl}
          size={meta.size}
        />
      {/if}

      <div class="dl-body">
        <div class="info-grid">
          <div class="info-cell">
            <div class="info-label">Uploaded</div>
            <div class="info-value">{formatTimestamp(meta.created_at)}</div>
          </div>
          <div class="info-cell">
            <div class="info-label expires-label-row">
              <span>Expires</span>
              {#if !editingExpiry}
                <button
                  type="button"
                  class="link-btn"
                  on:click={startEditExpiry}
                  aria-label="Edit expiry"
                >
                  Edit
                </button>
              {/if}
            </div>
            {#if editingExpiry}
              <div class="expiry-editor">
                <label class="never-row">
                  <input type="checkbox" bind:checked={expiryNeverChecked} />
                  Never expires
                </label>
                <input
                  type="datetime-local"
                  bind:value={expiryDateValue}
                  disabled={expiryNeverChecked || savingExpiry}
                />
                <div class="expiry-buttons">
                  <button
                    type="button"
                    class="btn-primary"
                    on:click={saveExpiry}
                    disabled={savingExpiry}
                  >
                    {savingExpiry ? 'Saving…' : 'Save'}
                  </button>
                  <button
                    type="button"
                    class="btn-secondary"
                    on:click={cancelEditExpiry}
                    disabled={savingExpiry}
                  >
                    Cancel
                  </button>
                </div>
              </div>
            {:else}
              <div class="info-value">{expiresLabel}</div>
            {/if}
          </div>
          <div class="info-cell">
            <div class="info-label">Size</div>
            <div class="info-value">{formatBytes(meta.size)}</div>
          </div>
          <div class="info-cell">
            <div class="info-label">Content-Type</div>
            <div class="info-value">{meta.mimeType || '—'}</div>
          </div>
          <div class="info-cell">
            <div class="info-label">ID</div>
            <div class="info-value">{fileid}</div>
          </div>
          <div class="info-cell">
            <div class="info-label">Status</div>
            <div class="info-value">
              {expiry.expired ? 'Expired (still on disk)' : 'Active'}
            </div>
          </div>
        </div>

        <div class="cli-block">
          <div class="cli-head">Fetch from terminal (admin)</div>
          <div class="cli-body">
            <span class="cmd"><span class="cli-prompt">$</span><span>{curlCommand}</span></span>
            <button
              class="btn-icon-sm"
              type="button"
              aria-label="Copy command"
              on:click={copyCli}
              disabled={!curlCommand}
            >
              {#if cliCopied}
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"><polyline points="20 6 9 17 4 12" /></svg
                >
              {:else}
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                  ><rect x="9" y="9" width="13" height="13" rx="2" ry="2" /><path
                    d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"
                  /></svg
                >
              {/if}
            </button>
          </div>
        </div>

        <div class="expiry"><span class="dot" class:expired={expiry.expired}></span> {expiryWords}</div>
      </div>
    </div>
  {/if}
</div>

{#if toastMessage}
  <div class="toast">{toastMessage}</div>
{/if}

<style>
  .topbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin: 0 0 12px;
    padding: 0 4px;
  }
  .back {
    color: var(--muted-foreground, #888);
    text-decoration: none;
    font-size: 13px;
  }
  .back:hover {
    color: var(--foreground);
  }
  .badge {
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px;
    font-weight: 500;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--muted-foreground, #888);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 4px 10px;
  }

  .dl-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
  }
  .file-head {
    padding: 16px 20px;
    display: flex;
    align-items: center;
    gap: 14px;
    border-bottom: 1px solid var(--border);
  }
  .file-icon-sm {
    flex-shrink: 0;
    width: 40px;
    height: 40px;
    border-radius: 8px;
    background: var(--muted);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--foreground);
  }
  .file-head-text {
    min-width: 0;
    flex: 1;
  }
  .file-name {
    font-size: 15px;
    font-weight: 600;
    letter-spacing: -0.01em;
    margin: 0 0 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .file-meta {
    font-size: 12px;
    color: var(--muted-foreground);
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .file-meta .sep {
    margin: 0 6px;
    opacity: 0.5;
  }
  .pill-expired {
    color: var(--danger, #c0392b);
    border: 1px solid var(--danger, #c0392b);
    border-radius: 999px;
    padding: 1px 8px;
    text-transform: uppercase;
    font-size: 10px;
    letter-spacing: 0.05em;
  }
  .head-actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .preview {
    background: var(--muted);
    border-bottom: 1px solid var(--border);
    position: relative;
  }
  .preview-empty {
    padding: 64px 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 12px;
    color: var(--muted-foreground);
    text-align: center;
  }
  .preview-empty .big-icon {
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: var(--card);
    border: 1px solid var(--border);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--foreground);
  }
  .preview-empty .big-icon :global(svg) {
    width: 28px;
    height: 28px;
  }
  .preview-empty .ext-badge {
    font-family: 'Geist Mono', ui-monospace, monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 3px 8px;
    border-radius: 999px;
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--muted-foreground);
  }
  .preview-empty .hint {
    font-size: 13px;
  }
  .preview-empty .hint.error {
    color: var(--danger, #c0392b);
  }

  .dl-body {
    padding: 20px 24px 24px;
  }
  .info-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0;
    margin-top: 0;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    overflow: hidden;
  }
  .info-cell {
    padding: 12px 14px;
  }
  .info-cell:nth-child(odd) {
    border-right: 1px solid var(--border);
  }
  .info-cell:nth-child(n + 3) {
    border-top: 1px solid var(--border);
  }
  .info-label {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--muted-foreground);
    margin-bottom: 4px;
  }
  .info-value {
    font-size: 13px;
    font-family: 'Geist Mono', ui-monospace, monospace;
    color: var(--foreground);
    word-break: break-all;
  }

  .cli-block {
    margin-top: 20px;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    overflow: hidden;
  }
  .cli-head {
    padding: 8px 14px;
    border-bottom: 1px solid var(--border);
    background: var(--muted);
    font-size: 12px;
    color: var(--muted-foreground);
    font-family: 'Geist Mono', ui-monospace, monospace;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .cli-body {
    padding: 12px 14px;
    font-family: 'Geist Mono', ui-monospace, monospace;
    font-size: 13px;
    line-height: 1.7;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .cli-body .cmd {
    flex: 1;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cli-body .cli-prompt {
    color: var(--muted-foreground);
    margin-right: 6px;
    user-select: none;
  }

  .expiry {
    margin-top: 14px;
    font-size: 12px;
    color: var(--muted-foreground);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }
  .expiry .dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: oklch(0.72 0.15 90);
    display: inline-block;
  }
  .expiry .dot.expired {
    background: var(--danger, #c0392b);
  }

  .toast {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 13px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }

  @media (max-width: 600px) {
    .info-grid {
      grid-template-columns: 1fr;
    }
    .info-cell:nth-child(odd) {
      border-right: 0;
    }
    .info-cell + .info-cell {
      border-top: 1px solid var(--border);
    }
    .file-head {
      flex-wrap: wrap;
    }
    .head-actions {
      width: 100%;
      justify-content: flex-end;
    }
  }

  .expires-label-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .link-btn {
    background: transparent;
    border: 0;
    padding: 0;
    color: var(--muted-foreground);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer;
    text-decoration: underline;
  }

  .link-btn:hover {
    color: var(--foreground);
  }

  .expiry-editor {
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-top: 6px;
  }

  .expiry-editor input[type='datetime-local'] {
    font: inherit;
    padding: 4px 6px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--background, transparent);
    color: var(--foreground);
  }

  .expiry-editor input[type='datetime-local']:disabled {
    opacity: 0.5;
  }

  .never-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: var(--muted-foreground);
  }

  .expiry-buttons {
    display: flex;
    gap: 6px;
  }
</style>
