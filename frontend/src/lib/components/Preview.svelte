<script lang="ts">
  import { onMount } from 'svelte';
  import { kindFromName, ICONS, extOf, type FileKind } from '$lib/utils/kind';

  export let filename: string;
  export let mimeType: string;
  export let downloadUrl: string;
  export let size: number;

  const TEXT_MAX_BYTES = 256 * 1024;

  $: kind = kindFromName(filename, mimeType) as FileKind;
  $: ext = extOf(filename) || 'file';

  let textContent: string | null = null;
  let textLoading = false;
  let textTooLarge = false;
  let textError: string | null = null;

  let audioEl: HTMLAudioElement | null = null;
  let isPlaying = false;
  let audioCurrent = 0;
  let audioDuration = 0;

  function fmtTime(seconds: number): string {
    if (!Number.isFinite(seconds) || seconds < 0) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  $: if (kind === 'text' && textContent === null && !textLoading && !textError) {
    if (size > TEXT_MAX_BYTES) {
      textTooLarge = true;
    } else {
      loadText();
    }
  }

  async function loadText(): Promise<void> {
    textLoading = true;
    textError = null;
    try {
      const res = await fetch(downloadUrl);
      if (!res.ok) {
        textError = `Failed (${res.status})`;
        return;
      }
      textContent = await res.text();
    } catch (err) {
      textError = err instanceof Error ? err.message : 'Failed to load preview';
    } finally {
      textLoading = false;
    }
  }

  function togglePlay(): void {
    if (!audioEl) return;
    if (audioEl.paused) {
      audioEl.play().catch(() => {});
    } else {
      audioEl.pause();
    }
  }

  function onAudioTimeUpdate(): void {
    if (!audioEl) return;
    audioCurrent = audioEl.currentTime;
  }

  function onAudioMeta(): void {
    if (!audioEl) return;
    audioDuration = Number.isFinite(audioEl.duration) ? audioEl.duration : 0;
  }

  function onAudioPlay(): void {
    isPlaying = true;
  }

  function onAudioPause(): void {
    isPlaying = false;
  }

  function seekAudio(ev: MouseEvent): void {
    if (!audioEl || !audioDuration) return;
    const target = ev.currentTarget as HTMLDivElement;
    const rect = target.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (ev.clientX - rect.left) / rect.width));
    audioEl.currentTime = ratio * audioDuration;
  }

  $: textLines = (textContent ?? '').split('\n');
</script>

<div class="preview">
  {#if kind === 'pdf'}
    <iframe
      class="preview-pdf"
      src={`${downloadUrl}#toolbar=0&navpanes=0`}
      title="PDF preview"
    ></iframe>
  {:else if kind === 'image'}
    <div class="preview-image">
      <img src={downloadUrl} alt={filename} />
    </div>
  {:else if kind === 'video'}
    <video class="preview-video" src={downloadUrl} controls preload="metadata"></video>
  {:else if kind === 'audio'}
    <div class="preview-audio">
      <audio
        bind:this={audioEl}
        src={downloadUrl}
        preload="metadata"
        on:timeupdate={onAudioTimeUpdate}
        on:loadedmetadata={onAudioMeta}
        on:play={onAudioPlay}
        on:pause={onAudioPause}
        on:ended={onAudioPause}
      ></audio>
      <div class="audio-head">
        <div class="audio-cover">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round">{@html ICONS.audio}</svg
          >
        </div>
        <div class="audio-titles">
          <div class="audio-title">{filename}</div>
          <div class="audio-sub">{mimeType}</div>
        </div>
      </div>
      <div class="audio-player">
        <button class="audio-btn" type="button" aria-label={isPlaying ? 'Pause' : 'Play'} on:click={togglePlay}>
          {#if isPlaying}
            <svg viewBox="0 0 24 24" fill="currentColor"
              ><rect x="6" y="5" width="4" height="14" /><rect x="14" y="5" width="4" height="14" /></svg
            >
          {:else}
            <svg viewBox="0 0 24 24" fill="currentColor"
              ><polygon points="6 4 20 12 6 20 6 4" /></svg
            >
          {/if}
        </button>
        <div class="audio-progress">
          <span class="audio-time-cur">{fmtTime(audioCurrent)}</span>
          <div
            class="audio-track"
            on:click={seekAudio}
            on:keydown={(e) => {
              if (!audioEl) return;
              if (e.key === 'ArrowRight') audioEl.currentTime = Math.min(audioDuration, audioEl.currentTime + 5);
              if (e.key === 'ArrowLeft') audioEl.currentTime = Math.max(0, audioEl.currentTime - 5);
            }}
            role="slider"
            tabindex="0"
            aria-label="Seek"
            aria-valuemin="0"
            aria-valuemax={audioDuration || 0}
            aria-valuenow={audioCurrent}
          >
            <div
              class="audio-track-fill"
              style="width: {audioDuration ? (audioCurrent / audioDuration) * 100 : 0}%"
            ></div>
          </div>
          <span class="audio-time-dur">{fmtTime(audioDuration)}</span>
        </div>
      </div>
    </div>
  {:else if kind === 'text'}
    {#if textLoading}
      <div class="preview-empty"><div class="hint">Loading preview…</div></div>
    {:else if textError}
      <div class="preview-empty"><div class="hint">{textError}</div></div>
    {:else if textTooLarge}
      <div class="preview-empty">
        <div class="big-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round">{@html ICONS.text}</svg
          >
        </div>
        <span class="ext-badge">{ext}</span>
        <div class="hint">File is too large to preview — use the Download button above.</div>
      </div>
    {:else if textContent !== null}
      <div class="preview-text">
        <table>
          <tbody>
            {#each textLines as line, i}
              <tr>
                <td class="ln">{i + 1}</td>
                <td class="code">{line || ' '}</td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {:else}
    <div class="preview-empty">
      <div class="big-icon">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.5"
          stroke-linecap="round"
          stroke-linejoin="round">{@html ICONS[kind] || ICONS.file}</svg
        >
      </div>
      <span class="ext-badge">{ext}</span>
      <div class="hint">No preview available — use the Download button above.</div>
    </div>
  {/if}
</div>

<style>
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

  .preview-pdf {
    width: 100%;
    height: 480px;
    border: 0;
    display: block;
    background: var(--card);
  }

  .preview-image {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    min-height: 320px;
  }
  .preview-image img {
    max-width: 100%;
    max-height: 480px;
    border-radius: calc(var(--radius) - 4px);
    display: block;
  }

  .preview-video {
    width: 100%;
    display: block;
    background: black;
    max-height: 480px;
  }

  .preview-audio {
    padding: 28px 24px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .audio-head {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .audio-cover {
    width: 56px;
    height: 56px;
    border-radius: 10px;
    background: linear-gradient(135deg, oklch(0.55 0.14 280), oklch(0.6 0.13 320));
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: white;
    flex-shrink: 0;
  }
  .audio-cover :global(svg) {
    width: 22px;
    height: 22px;
  }
  .audio-titles {
    min-width: 0;
    flex: 1;
  }
  .audio-title {
    font-size: 14px;
    font-weight: 600;
    margin: 0 0 2px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .audio-sub {
    font-size: 12px;
    color: var(--muted-foreground);
    font-family: 'Geist Mono', ui-monospace, monospace;
  }

  .audio-player {
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .audio-btn {
    width: 40px;
    height: 40px;
    border-radius: 999px;
    border: 0;
    background: var(--primary);
    color: var(--primary-foreground);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    flex-shrink: 0;
    transition: opacity 0.15s ease;
  }
  .audio-btn:hover {
    opacity: 0.9;
  }
  .audio-btn :global(svg) {
    width: 14px;
    height: 14px;
  }
  .audio-progress {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .audio-time-cur,
  .audio-time-dur {
    font-family: 'Geist Mono', ui-monospace, monospace;
    font-size: 11px;
    color: var(--muted-foreground);
    min-width: 34px;
  }
  .audio-time-dur {
    text-align: right;
  }
  .audio-track {
    flex: 1;
    height: 4px;
    border-radius: 2px;
    background: var(--border);
    position: relative;
    cursor: pointer;
    overflow: hidden;
  }
  .audio-track-fill {
    position: absolute;
    inset: 0 auto 0 0;
    background: var(--foreground);
    border-radius: 2px;
  }

  .preview-text {
    background: var(--card);
    max-height: 420px;
    overflow: auto;
    font-family: 'Geist Mono', ui-monospace, monospace;
    font-size: 12.5px;
    line-height: 1.65;
    padding: 0;
  }
  .preview-text table {
    border-collapse: collapse;
    width: 100%;
  }
  .preview-text .ln {
    width: 40px;
    text-align: right;
    padding: 0 12px;
    color: var(--muted-foreground);
    border-right: 1px solid var(--border);
    user-select: none;
    vertical-align: top;
  }
  .preview-text .code {
    padding: 0 14px;
    white-space: pre;
    color: var(--foreground);
  }
</style>
