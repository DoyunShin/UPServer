<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { uploadFile, APIError } from '$lib/api';
  import { setOwnerKey } from '$lib/stores/owner';

  type Status = 'idle' | 'uploading' | 'error';

  let dragging = false;
  let status: Status = 'idle';
  let progress = 0;
  let currentName = 'hello.txt';
  let errorMessage = '';
  let copied = false;
  let fileInput: HTMLInputElement;

  let host = '';
  onMount(() => {
    host = `${window.location.protocol}//${window.location.host}`;
  });

  $: command =
    status === 'uploading'
      ? `Uploading ${currentName}  (${progress}%)…`
      : status === 'error'
        ? `Error: ${errorMessage}`
        : `curl --upload-file ${currentName} ${host}/${encodeURIComponent(currentName)}`;

  function openFilePicker(): void {
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
    dragging = true;
  }

  function onDragLeave(ev: DragEvent): void {
    ev.preventDefault();
    dragging = false;
  }

  function onDrop(ev: DragEvent): void {
    ev.preventDefault();
    dragging = false;
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
    const handle = uploadFile(file, (loaded, total) => {
      progress = total > 0 ? Math.round((loaded / total) * 100) : 0;
    });
    try {
      const result = await handle.promise;
      if (result.ownerKey) {
        setOwnerKey(result.fileid, result.ownerKey);
      }
      await goto(`/${encodeURIComponent(result.fileid)}/${encodeURIComponent(result.filename)}`);
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

  async function copyCommand(): Promise<void> {
    try {
      await navigator.clipboard.writeText(command);
      copied = true;
      setTimeout(() => (copied = false), 1400);
    } catch {
      /* clipboard unavailable */
    }
  }
</script>

<div class="wrap">
  <div class="card">
    <div class="prompt-bar">
      <div class="prompt-text">
        <span class="chev">$</span><span>{command}</span>
      </div>
      <button
        class="btn-icon-sm"
        type="button"
        aria-label="Copy command"
        on:click={copyCommand}
        disabled={status === 'uploading'}
      >
        {#if copied}
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
  }
</style>
