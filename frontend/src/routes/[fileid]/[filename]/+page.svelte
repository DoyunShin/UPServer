<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import Preview from '$lib/components/Preview.svelte';
  import { ICONS, kindFromName } from '$lib/utils/kind';
  import {
    formatBytes,
    formatTimestamp,
    formatRelativeFromSeconds,
    formatRelativeWords,
    computeExpiry
  } from '$lib/utils/format';
  import { APIError, deleteFile } from '$lib/api';
  import { getOwnerKey, clearOwnerKey } from '$lib/stores/owner';
  import type { PageData } from './$types';

  export let data: PageData;

  $: meta = data.meta;
  $: notFound = data.errorStatus === 404 || (data.errorStatus !== null && !meta);
  $: kind = meta ? kindFromName(meta.name, meta.mimeType) : 'file';

  let host = '';
  let ownerKey: string | null = null;
  let cliCopied = false;
  let confirmingDelete = false;
  let deleting = false;
  let toastMessage = '';

  $: encodedPath = `${encodeURIComponent(data.fileid)}/${encodeURIComponent(data.filename)}`;
  $: downloadUrl = `/get/${encodedPath}`;
  $: curlCommand = host ? `curl -O ${host}/${encodedPath}` : `curl -O /${encodedPath}`;

  onMount(() => {
    host = `${window.location.protocol}//${window.location.host}`;
    ownerKey = getOwnerKey(data.fileid);
  });

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

  function downloadFile(): void {
    if (!downloadUrl) return;
    window.location.href = downloadUrl;
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

  async function confirmDelete(): Promise<void> {
    if (!ownerKey || !meta || deleting) return;
    deleting = true;
    try {
      await deleteFile(data.fileid, data.filename, ownerKey);
      clearOwnerKey(data.fileid);
      toastMessage = 'File deleted';
      setTimeout(() => goto('/'), 600);
    } catch (err) {
      if (err instanceof APIError && err.status === 403) {
        clearOwnerKey(data.fileid);
        ownerKey = null;
        toastMessage = 'Owner key rejected';
      } else {
        toastMessage = err instanceof Error ? err.message : 'Delete failed';
      }
      setTimeout(() => (toastMessage = ''), 3000);
    } finally {
      deleting = false;
      confirmingDelete = false;
    }
  }
</script>

<div class="wrap-narrow">
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
        <h1 class="file-name">{meta?.name ?? data.filename}</h1>
        <div class="file-meta">
          <span>{meta ? formatBytes(meta.size) : '—'}</span>
          <span class="sep">·</span>
          <span>{meta?.mimeType ?? 'unknown'}</span>
        </div>
      </div>
      <div class="head-actions">
        {#if ownerKey && meta}
          {#if confirmingDelete}
            <button class="btn-danger" type="button" disabled={deleting} on:click={confirmDelete}>
              {deleting ? 'Deleting…' : 'Confirm delete'}
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
              aria-label="Delete file"
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
              Delete
            </button>
          {/if}
        {/if}
        <button
          class="btn-primary"
          type="button"
          on:click={downloadFile}
          disabled={!meta}
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
          Download
        </button>
      </div>
    </div>

    {#if notFound}
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
          <div class="hint">File not found or it has expired.</div>
        </div>
      </div>
    {:else if meta}
      <Preview
        filename={meta.name}
        mimeType={meta.mimeType}
        {downloadUrl}
        size={meta.size}
      />
    {:else}
      <div class="preview">
        <div class="preview-empty"><div class="hint">Loading…</div></div>
      </div>
    {/if}

    <div class="dl-body">
      <div class="info-grid">
        <div class="info-cell">
          <div class="info-label">Uploaded</div>
          <div class="info-value">
            {meta ? formatTimestamp(meta.created_at) : '—'}
          </div>
        </div>
        <div class="info-cell">
          <div class="info-label">Expires</div>
          <div class="info-value">{meta ? expiresLabel : '—'}</div>
        </div>
        <div class="info-cell">
          <div class="info-label">Size</div>
          <div class="info-value">{meta ? formatBytes(meta.size) : '—'}</div>
        </div>
        <div class="info-cell">
          <div class="info-label">Content-Type</div>
          <div class="info-value">{meta?.mimeType ?? '—'}</div>
        </div>
      </div>

      <div class="cli-block">
        <div class="cli-head">Fetch from terminal</div>
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

      {#if meta}
        <div class="expiry"><span class="dot"></span> {expiryWords}</div>
      {/if}
    </div>
  </div>
</div>

{#if toastMessage}
  <div class="toast">{toastMessage}</div>
{/if}

<style>
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
  .info-cell + .info-cell {
    border-left: 1px solid var(--border);
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

  @media (max-width: 600px) {
    .info-grid {
      grid-template-columns: 1fr;
    }
    .info-cell + .info-cell {
      border-left: 0;
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
</style>
