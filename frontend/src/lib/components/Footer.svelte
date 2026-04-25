<script lang="ts">
  import { info } from '$lib/stores/info';
  import { safeHref, sanitizeRichText } from '$lib/utils/sanitize';

  $: columns = $info.data?.webinfo ?? [];
  $: brandName = $info.data?.brand ?? '';
  $: brandInfoSafe = sanitizeRichText($info.data?.info);
</script>

<footer class="footer">
  <div class="footer-inner">
    <div class="footer-grid">
      {#each columns as col}
        <div class="footer-col">
          <h5>{col[0]}</h5>
          <ul>
            {#each col.slice(1) as item}
              {#if Array.isArray(item)}
                <li><a href={safeHref(item[1])}>{item[0]}</a></li>
              {/if}
            {/each}
          </ul>
        </div>
      {/each}
      <div class="footer-col brand-block">
        <div class="brand-row">
          <span class="brand-logo" aria-hidden="true"></span>
          <span class="brand-title">{brandName}</span>
        </div>
        {#if brandInfoSafe}
          <div class="brand-desc">{@html brandInfoSafe}</div>
        {/if}
      </div>
    </div>
    <div class="footer-bottom">
      <span class="footer-copy">Copyright © 2023 DoyunShin</span>
      <div class="footer-social">
        <a href="/" aria-label="Home">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            ><path d="M3 12l9-9 9 9" /><path d="M5 10v10h14V10" /></svg
          >
        </a>
        <a href="https://github.com/DoyunShin" aria-label="GitHub" target="_blank" rel="noopener">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            ><path
              d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22"
            /></svg
          >
        </a>
      </div>
    </div>
  </div>
</footer>

<style>
  .footer {
    border-top: 1px solid var(--border);
    padding: 40px 0 20px;
  }
  .footer-inner {
    max-width: 1120px;
    margin: 0 auto;
    padding: 0 32px;
  }
  .footer-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 32px;
    padding-bottom: 28px;
  }
  .footer-col h5 {
    font-size: 13px;
    font-weight: 600;
    margin: 0 0 12px;
    color: var(--foreground);
  }
  .footer-col ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .footer-col a {
    color: var(--muted-foreground);
    text-decoration: none;
    font-size: 13px;
    transition: color 0.15s ease;
  }
  .footer-col a:hover {
    color: var(--foreground);
  }
  .brand-block {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .brand-block .brand-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .brand-block .brand-logo {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: linear-gradient(135deg, oklch(0.72 0.12 320), oklch(0.72 0.1 40));
  }
  .brand-block .brand-title {
    font-size: 13px;
    font-weight: 700;
    color: var(--foreground);
  }
  .brand-block .brand-desc {
    font-size: 13px;
    color: var(--muted-foreground);
  }
  .brand-block .brand-desc :global(.b) {
    color: var(--foreground);
    font-weight: 600;
  }
  .footer-bottom {
    border-top: 1px solid var(--border);
    padding-top: 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }
  .footer-copy {
    font-size: 13px;
    color: var(--muted-foreground);
  }
  .footer-social {
    display: flex;
    gap: 4px;
  }
  .footer-social a {
    width: 32px;
    height: 32px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    color: var(--muted-foreground);
    border-radius: calc(var(--radius) - 4px);
    transition:
      color 0.15s ease,
      background 0.15s ease;
  }
  .footer-social a:hover {
    color: var(--foreground);
    background: var(--secondary);
  }
  .footer-social :global(svg) {
    width: 14px;
    height: 14px;
  }

  @media (max-width: 600px) {
    .footer-grid {
      grid-template-columns: 1fr 1fr;
      gap: 24px;
    }
    .footer-inner {
      padding: 0 20px;
    }
  }
</style>
