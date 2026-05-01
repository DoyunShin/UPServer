<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    APIError,
    fetchAdminFile,
    fetchMeta,
    type FileMetadata
  } from '$lib/api';
  import { readAdminSession, clearAdminSession } from '$lib/stores/admin-session';
  import {
    formatBytes,
    formatTimestamp,
    formatRelativeWords,
    computeExpiry
  } from '$lib/utils/format';

  type Status = 'idle' | 'loading' | 'ready' | 'unauthenticated' | 'notfound' | 'error';

  let status: Status = 'idle';
  let errorMessage = '';
  let meta: FileMetadata | null = null;
  let downloading = false;

  $: fileid = $page.params.fileid ?? '';
  $: filename = $page.params.filename ?? '';

  $: expiry = meta
    ? computeExpiry(meta.created_at, meta.delete_after)
    : { enabled: false, expired: false, remainingSeconds: 0, expiresAt: 0 };

  $: expiresLabel = !expiry.enabled
    ? 'Never'
    : expiry.expired
      ? 'Expired'
      : `in ${formatRelativeWords(expiry.remainingSeconds)}`;

  async function load(): Promise<void> {
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    status = 'loading';
    errorMessage = '';
    try {
      meta = await fetchMeta(fileid, filename, fetch, { bearerToken: session.token });
      status = 'ready';
    } catch (err) {
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
        errorMessage = err instanceof Error ? err.message : 'Download failed';
        setTimeout(() => (errorMessage = ''), 3000);
      }
    } finally {
      downloading = false;
    }
  }

  onMount(() => {
    load();
  });
</script>

<svelte:head>
  <title>{filename} · Admin</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<section class="wrap">
  <div class="head">
    <a class="back" href="/admin">← Back to admin</a>
    <span class="badge">Admin</span>
  </div>

  {#if status === 'idle' || status === 'loading'}
    <p class="muted">Loading…</p>
  {:else if status === 'unauthenticated'}
    <div class="card">
      <p class="error" role="alert">{errorMessage || 'Sign in required.'}</p>
      <a class="btn btn-primary" href="/admin">Go to admin sign-in</a>
    </div>
  {:else if status === 'notfound'}
    <div class="card">
      <h2>File not found</h2>
      <p class="muted">No file with id <code>{fileid}</code> and name <code>{filename}</code>.</p>
      <a class="btn btn-ghost" href="/admin">Back</a>
    </div>
  {:else if status === 'error'}
    <div class="card">
      <p class="error" role="alert">{errorMessage}</p>
      <button type="button" class="btn btn-ghost" on:click={load}>Retry</button>
    </div>
  {:else if meta}
    <div class="card">
      <div class="filehead">
        <h1 class="filename">{meta.name}</h1>
        <div class="meta-row">
          <span>{formatBytes(meta.size)}</span>
          <span class="sep">·</span>
          <span class="mono">{meta.mimeType || 'unknown'}</span>
          {#if expiry.expired}
            <span class="sep">·</span>
            <span class="pill expired">expired</span>
          {/if}
        </div>
      </div>

      <dl class="grid">
        <dt>ID</dt>
        <dd class="mono">{fileid}</dd>

        <dt>Uploaded</dt>
        <dd>{formatTimestamp(meta.created_at)}</dd>

        <dt>Expires</dt>
        <dd>
          {expiresLabel}
          {#if expiry.enabled}
            <span class="muted small"> · {formatTimestamp(expiry.expiresAt)}</span>
          {/if}
        </dd>

        <dt>Size</dt>
        <dd>{formatBytes(meta.size)}</dd>
      </dl>

      <div class="actions">
        <button
          type="button"
          class="btn btn-primary"
          on:click={downloadFile}
          disabled={downloading}
        >
          {downloading ? 'Downloading…' : 'Download'}
        </button>
        {#if errorMessage}
          <span class="error" role="alert">{errorMessage}</span>
        {/if}
      </div>
    </div>
  {/if}
</section>

<style>
  .wrap {
    max-width: 760px;
    margin: 0 auto;
    padding: 24px 16px 48px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .back {
    color: var(--muted-foreground, #888);
    text-decoration: none;
    font-size: 14px;
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

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .filehead {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .filename {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    word-break: break-all;
  }

  .meta-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    color: var(--muted-foreground, #888);
    font-size: 14px;
  }

  .sep {
    color: var(--muted-foreground, #888);
  }

  .pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    padding: 2px 8px;
    border-radius: 999px;
    border: 1px solid var(--border);
  }

  .pill.expired {
    color: var(--danger, #c0392b);
    border-color: var(--danger, #c0392b);
  }

  .grid {
    display: grid;
    grid-template-columns: 120px 1fr;
    gap: 8px 16px;
    margin: 0;
    font-size: 14px;
  }

  .grid dt {
    color: var(--muted-foreground, #888);
    font-weight: 500;
  }

  .grid dd {
    margin: 0;
    word-break: break-all;
  }

  .small {
    font-size: 13px;
  }

  .muted {
    color: var(--muted-foreground, #888);
  }

  .mono,
  code {
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px;
  }

  code {
    background: color-mix(in oklch, var(--card) 80%, transparent);
    padding: 1px 4px;
    border-radius: 4px;
  }

  .actions {
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 36px;
    padding: 0 14px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--foreground);
    transition: background 120ms ease, color 120ms ease, border-color 120ms ease;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--primary);
    color: var(--primary-foreground);
    border-color: var(--primary);
  }

  .btn-primary:hover:not(:disabled) {
    background: color-mix(in oklch, var(--primary) 90%, transparent);
  }

  .btn-ghost {
    background: transparent;
  }

  .btn-ghost:hover {
    background: color-mix(in oklch, var(--foreground) 6%, transparent);
  }

  .error {
    color: var(--danger, #c0392b);
    margin: 0;
  }
</style>
