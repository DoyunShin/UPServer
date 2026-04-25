<script lang="ts">
  import { onMount } from 'svelte';
  import { info } from '$lib/stores/info';
  import { theme, applyTheme, toggleTheme } from '$lib/stores/theme';
  import { safeHref } from '$lib/utils/sanitize';

  const SUN =
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/>';
  const MOON = '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>';

  onMount(() => {
    applyTheme($theme);
  });

  $: contactHref = safeHref($info.data?.contact);
  $: brandName = $info.data?.name || 'upload.sh';
  $: themeIcon = $theme === 'dark' ? SUN : MOON;
</script>

<nav class="nav">
  <div class="nav-inner">
    <a class="brand" href="/" aria-label="upload home">
      <span class="brand-mark" aria-hidden="true">
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.25"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
      </span>
      <span class="brand-name">{brandName}</span>
    </a>
    <div class="nav-links">
      <a class="nav-link" href="/">Home</a>
      {#if $info.data?.contact}
        <a class="nav-link" href={contactHref}>Contacts</a>
      {/if}
      <button class="theme-btn" type="button" aria-label="Toggle theme" on:click={toggleTheme}>
        <svg
          width="15"
          height="15"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round">{@html themeIcon}</svg
        >
      </button>
    </div>
  </div>
</nav>

<style>
  .nav {
    position: sticky;
    top: 0;
    z-index: 40;
    height: 56px;
    background: color-mix(in oklch, var(--background) 80%, transparent);
    backdrop-filter: saturate(180%) blur(10px);
    -webkit-backdrop-filter: saturate(180%) blur(10px);
    border-bottom: 1px solid var(--border);
  }
  .nav-inner {
    max-width: 920px;
    margin: 0 auto;
    padding: 0 24px;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .brand {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 600;
    letter-spacing: -0.01em;
    color: var(--foreground);
    text-decoration: none;
  }
  .brand-mark {
    width: 26px;
    height: 26px;
    border-radius: 7px;
    background: var(--foreground);
    color: var(--background);
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .brand-name {
    font-size: 14px;
  }
  .nav-links {
    display: flex;
    gap: 2px;
    margin-left: auto;
    align-items: center;
  }
  .nav-link {
    display: inline-flex;
    align-items: center;
    height: 32px;
    padding: 0 12px;
    border-radius: calc(var(--radius) - 4px);
    font-size: 13px;
    font-weight: 500;
    color: var(--muted-foreground);
    text-decoration: none;
    transition:
      color 0.15s ease,
      background 0.15s ease;
    cursor: pointer;
    background: none;
    border: 0;
  }
  .nav-link:hover {
    color: var(--foreground);
    background: var(--secondary);
  }
  .theme-btn {
    margin-left: 4px;
    width: 32px;
    height: 32px;
    border-radius: calc(var(--radius) - 4px);
    border: 1px solid var(--border);
    background: transparent;
    color: var(--foreground);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: background 0.15s ease;
  }
  .theme-btn:hover {
    background: var(--secondary);
  }
</style>
