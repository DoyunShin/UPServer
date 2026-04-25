<script lang="ts">
  import { onMount } from 'svelte';
  import { uploadFile, APIError } from '$lib/api';
  import { setOwnerKey } from '$lib/stores/owner';

  type Status = 'idle' | 'uploading' | 'success' | 'error';

  interface UploadResultUI {
    url: string;
    fileid: string;
    filename: string;
    ownerKey: string | null;
    detailPath: string;
  }

  let dragging = false;
  let status: Status = 'idle';
  let progress = 0;
  let currentName = 'hello.txt';
  let errorMessage = '';
  let result: UploadResultUI | null = null;

  let fileInput: HTMLInputElement;
  let host = '';

  let promptCopied = false;
  let keyCopied = false;
  let keyRevealed = false;

  onMount(() => {
    host = `${window.location.protocol}//${window.location.host}`;
  });

  $: promptText =
    status === 'uploading'
      ? `Uploading ${currentName}  (${progress}%)…`
      : status === 'error'
        ? `Error: ${errorMessage}`
        : status === 'success' && result
          ? result.url
          : `curl --upload-file ${currentName} ${host}/${encodeURIComponent(currentName)}`;

  function openFilePicker(): void {
    if (status === 'uploading') return;
    fileInput?.click();
  }

  function onFileChange(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      handleFile(input.files[0]);
      input.value = '';
    }
  }

  function onDragOver(ev: DragEvent): void {
    ev.preventDefault();
    if (status === 'uploading') return;
    dragging = true;
  }

  function onDragLeave(ev: DragEvent): void {
    ev.preventDefault();
    dragging = false;
  }

  function onDrop(ev: DragEvent): void {
    ev.preventDefault();
    dragging = false;
    if (status === 'uploading') return;
    if (ev.dataTransfer?.files && ev.dataTransfer.files.length > 0) {
      handleFile(ev.dataTransfer.files[0]);
    }
  }

  async function handleFile(file: File): Promise<void> {
    if (status === 'uploading') return;
    currentName = file.name;
    status = 'uploading';
    progress = 0;
    errorMessage = '';
    result = null;
    keyRevealed = false;
    keyCopied = false;

    const handle = uploadFile(file, (loaded, total) => {
      progress = total > 0 ? Math.round((loaded / total) * 100) : 0;
    });
    try {
      const r = await handle.promise;
      if (r.ownerKey) {
        setOwnerKey(r.fileid, r.ownerKey);
      }
      result = {
        url: r.url,
        fileid: r.fileid,
        filename: r.filename,
        ownerKey: r.ownerKey,
        detailPath: `/${encodeURIComponent(r.fileid)}/${encodeURIComponent(r.filename)}`
      };
      status = 'success';
    } catch (err) {
      status = 'error';
      errorMessage =
        err instanceof APIError ? err.message : err instanceof Error ? err.message : 'Upload failed';
      setTimeout(() => {
        if (status === 'error') {
          status = 'idle';
          errorMessage = '';
        }
      }, 4000);
    }
  }

  function reset(): void {
    status = 'idle';
    result = null;
    currentName = 'hello.txt';
    progress = 0;
    errorMessage = '';
    keyRevealed = false;
    keyCopied = false;
    promptCopied = false;
  }

  async function copyText(value: string, onCopy: () => void): Promise<void> {
    try {
      await navigator.clipboard.writeText(value);
      onCopy();
    } catch {
      /* clipboard unavailable */
    }
  }

  function copyPrompt(): void {
    copyText(promptText, () => {
      promptCopied = true;
      setTimeout(() => (promptCopied = false), 1400);
    });
  }

  function copyKey(): void {
    if (!result?.ownerKey) return;
    copyText(result.ownerKey, () => {
      keyCopied = true;
      setTimeout(() => (keyCopied = false), 1400);
    });
  }
</script>

<div class="wrap">
  <div class="card">
    <div class="prompt-bar" class:success={status === 'success'} class:error={status === 'error'}>
      <div class="prompt-text">
        <span class="chev">$</span>
        {#if status === 'success' && result}
          <a class="prompt-link" href={result.url} target="_blank" rel="noopener">{result.url}</a>
        {:else}
          <span>{promptText}</span>
        {/if}
      </div>
      <button
        class="btn-icon-sm"
        type="button"
        aria-label="Copy"
        on:click={copyPrompt}
        disabled={status === 'uploading'}
      >
        {#if promptCopied}
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

    {#if status === 'success' && result}
      <div class="result">
        <div class="result-head">
          <div class="result-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.25"
              stroke-linecap="round"
              stroke-linejoin="round"><polyline points="20 6 9 17 4 12" /></svg
            >
          </div>
          <div class="result-titles">
            <div class="result-title">Upload complete</div>
            <div class="result-sub">{result.filename}</div>
          </div>
        </div>

        {#if result.ownerKey}
          <div class="key-block">
            <div class="key-label">
              Owner key
              <span class="key-hint">— save this to delete the file later</span>
            </div>
            <div class="key-row">
              <code class="key-value" class:revealed={keyRevealed}
                >{keyRevealed ? result.ownerKey : '•'.repeat(result.ownerKey.length)}</code
              >
              <button
                class="btn-secondary"
                type="button"
                on:click={() => (keyRevealed = !keyRevealed)}
                aria-label={keyRevealed ? 'Hide owner key' : 'Show owner key'}
              >
                {keyRevealed ? 'Hide' : 'Show'}
              </button>
              <button class="btn-primary" type="button" on:click={copyKey}>
                {keyCopied ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>
        {/if}

        <div class="result-actions">
          <a class="btn-secondary" href={result.detailPath}>Open file page</a>
          <button class="btn-primary" type="button" on:click={reset}>Upload another</button>
        </div>
      </div>
    {:else}
      <div
        class="dropzone"
        class:dragging
        class:uploading={status === 'uploading'}
        on:click={openFilePicker}
        on:dragover={onDragOver}
        on:dragleave={onDragLeave}
        on:drop={onDrop}
        role="presentation"
      >
        {#if status === 'uploading'}
          <h1 class="drop-title">{progress}%</h1>
          <p class="drop-sub">Uploading {currentName}…</p>
        {:else}
          <h1 class="drop-title">Drag a file here</h1>
          <p class="drop-sub">
            or
            <button
              class="link-btn"
              type="button"
              on:click|stopPropagation={openFilePicker}>click here</button
            >
            to choose a file
          </p>
        {/if}
        <input
          type="file"
          bind:this={fileInput}
          on:change={onFileChange}
          aria-label="Choose file to upload"
          hidden
        />
      </div>
    {/if}
  </div>
</div>

<style>
  .prompt-bar {
    background: var(--card);
    border-bottom: 1px solid var(--border);
    padding: 6px 16px;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .prompt-bar.success {
    background: color-mix(in oklch, var(--card) 92%, oklch(0.72 0.18 145) 8%);
  }
  .prompt-bar.error {
    background: color-mix(in oklch, var(--card) 92%, var(--danger) 12%);
  }
  .prompt-text {
    flex: 1;
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 14px;
    color: var(--foreground);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .prompt-text .chev {
    color: var(--muted-foreground);
    margin-right: 8px;
  }
  .prompt-link {
    color: var(--foreground);
    text-decoration: underline;
    text-underline-offset: 3px;
  }
  .prompt-link:hover {
    color: var(--muted-foreground);
  }

  .dropzone {
    background: var(--muted);
    min-height: 380px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 40px 20px;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .dropzone:hover {
    background: color-mix(in oklch, var(--muted) 80%, var(--foreground) 4%);
  }
  .dropzone.dragging {
    background: color-mix(in oklch, var(--muted) 70%, var(--foreground) 8%);
    box-shadow: inset 0 0 0 1.5px var(--foreground);
  }
  .dropzone.uploading {
    cursor: progress;
  }
  .drop-title {
    font-size: 56px;
    font-weight: 500;
    line-height: 1.1;
    letter-spacing: -0.025em;
    margin: 0 0 12px;
  }
  .drop-sub {
    font-size: 16px;
    color: var(--muted-foreground);
    margin: 0;
  }
  .link-btn {
    background: none;
    border: 0;
    padding: 0;
    font: inherit;
    color: var(--foreground);
    text-decoration: underline;
    text-underline-offset: 3px;
    cursor: pointer;
  }
  .link-btn:hover {
    color: var(--muted-foreground);
  }

  .result {
    background: var(--muted);
    padding: 32px 28px;
    display: flex;
    flex-direction: column;
    gap: 24px;
    min-height: 380px;
    justify-content: center;
  }
  .result-head {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .result-icon {
    width: 44px;
    height: 44px;
    border-radius: 12px;
    background: var(--card);
    border: 1px solid var(--border);
    color: oklch(0.72 0.18 145);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .result-icon svg {
    width: 22px;
    height: 22px;
  }
  .result-titles {
    min-width: 0;
    flex: 1;
  }
  .result-title {
    font-size: 18px;
    font-weight: 600;
    letter-spacing: -0.015em;
    margin: 0 0 2px;
  }
  .result-sub {
    font-size: 13px;
    color: var(--muted-foreground);
    font-family: 'Geist Mono', ui-monospace, monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .key-block {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    padding: 14px 16px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .key-label {
    font-size: 12px;
    font-weight: 600;
    color: var(--foreground);
  }
  .key-hint {
    font-weight: 400;
    color: var(--muted-foreground);
    margin-left: 4px;
  }
  .key-row {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }
  .key-value {
    flex: 1;
    min-width: 140px;
    font-family: 'Geist Mono', ui-monospace, monospace;
    font-size: 14px;
    letter-spacing: 0.05em;
    background: var(--muted);
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 4px);
    padding: 8px 12px;
    color: var(--muted-foreground);
    overflow: hidden;
    text-overflow: ellipsis;
    user-select: all;
  }
  .key-value.revealed {
    color: var(--foreground);
    letter-spacing: 0.02em;
  }

  .result-actions {
    display: flex;
    gap: 8px;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  @media (max-width: 600px) {
    .drop-title {
      font-size: 36px;
    }
    .drop-sub {
      font-size: 14px;
    }
    .prompt-text {
      font-size: 12.5px;
    }
    .dropzone {
      min-height: 280px;
    }
    .result {
      padding: 24px 20px;
    }
    .result-actions {
      justify-content: stretch;
    }
    .result-actions :global(.btn-primary),
    .result-actions :global(.btn-secondary) {
      flex: 1;
    }
  }
</style>
