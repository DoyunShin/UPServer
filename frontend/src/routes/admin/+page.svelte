<script lang="ts">
  import { onMount } from 'svelte';
  import {
    APIError,
    adminLogin,
    adminLogout,
    fetchAdminFiles,
    type AdminFileItem,
    type AdminFilesData
  } from '$lib/api';
  import {
    readAdminSession,
    writeAdminSession,
    clearAdminSession
  } from '$lib/stores/admin-session';
  import {
    formatBytes,
    formatTimestamp,
    formatRelativeWords
  } from '$lib/utils/format';

  type Status = 'idle' | 'unauthenticated' | 'loading' | 'ready' | 'error' | 'disabled';

  let status: Status = 'idle';
  let passwordInput = '';
  let errorMessage = '';
  let files: AdminFilesData = { active: [], expired: [] };
  let now = Math.floor(Date.now() / 1000);
  let sessionExpiresAt = 0;

  async function loadFiles(token: string): Promise<void> {
    status = 'loading';
    errorMessage = '';
    try {
      files = await fetchAdminFiles(token);
      now = Math.floor(Date.now() / 1000);
      status = 'ready';
    } catch (err) {
      if (err instanceof APIError) {
        if (err.status === 401) {
          clearAdminSession();
          errorMessage = 'Session expired. Please sign in again.';
          status = 'unauthenticated';
          return;
        }
        if (err.status === 404) {
          clearAdminSession();
          errorMessage = '';
          status = 'disabled';
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

  async function onSubmitLogin(ev: Event): Promise<void> {
    ev.preventDefault();
    const candidate = passwordInput;
    if (!candidate) {
      errorMessage = 'Enter the admin password.';
      return;
    }
    status = 'loading';
    errorMessage = '';
    try {
      const result = await adminLogin(candidate);
      writeAdminSession({ token: result.token, expires_at: result.expires_at });
      sessionExpiresAt = result.expires_at;
      passwordInput = '';
      await loadFiles(result.token);
    } catch (err) {
      if (err instanceof APIError) {
        if (err.status === 403) {
          errorMessage = 'Wrong password.';
          status = 'unauthenticated';
          return;
        }
        if (err.status === 404) {
          errorMessage = '';
          status = 'disabled';
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

  async function onSignOut(): Promise<void> {
    const session = readAdminSession();
    clearAdminSession();
    files = { active: [], expired: [] };
    errorMessage = '';
    sessionExpiresAt = 0;
    status = 'unauthenticated';
    if (session) {
      try {
        await adminLogout(session.token);
      } catch {
        /* server-side revoke is best-effort; local state is already cleared */
      }
    }
  }

  async function onRetry(): Promise<void> {
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    sessionExpiresAt = session.expires_at;
    await loadFiles(session.token);
  }

  function ageWords(item: AdminFileItem): string {
    const seconds = Math.max(0, now - item.created_at);
    return formatRelativeWords(seconds) + ' ago';
  }

  function expiresWords(item: AdminFileItem): string {
    if (item.expires_at == null) return 'never';
    const remaining = Math.floor(item.expires_at - now);
    if (remaining <= 0) {
      const overdue = -remaining;
      return formatRelativeWords(overdue) + ' overdue';
    }
    return 'in ' + formatRelativeWords(remaining);
  }

  function expiresAbsolute(item: AdminFileItem): string {
    if (item.expires_at == null) return '—';
    return formatTimestamp(item.expires_at);
  }

  onMount(async () => {
    const session = readAdminSession();
    if (!session) {
      status = 'unauthenticated';
      return;
    }
    sessionExpiresAt = session.expires_at;
    await loadFiles(session.token);
  });
</script>

<svelte:head>
  <title>Admin · UPServer</title>
  <meta name="robots" content="noindex" />
</svelte:head>

<section class="admin">
  <header class="admin-head">
    <h1>Admin</h1>
    {#if status === 'ready'}
      <div class="head-right">
        {#if sessionExpiresAt > now}
          <span class="muted small">
            Session: {formatRelativeWords(sessionExpiresAt - now)} left
          </span>
        {/if}
        <button type="button" class="ghost" on:click={onSignOut}>Sign out</button>
      </div>
    {/if}
  </header>

  {#if status === 'idle' || status === 'loading'}
    <p class="muted">Loading…</p>
  {:else if status === 'disabled'}
    <div class="card">
      <h2>Admin is disabled</h2>
      <p>
        Set <code>host.admin_token</code> in <code>config.json</code> to a non-empty
        value and restart the server to enable this page.
      </p>
    </div>
  {:else if status === 'unauthenticated'}
    <form class="card login" on:submit={onSubmitLogin}>
      <label for="admin-pwd">Admin password</label>
      <input
        id="admin-pwd"
        type="password"
        autocomplete="current-password"
        bind:value={passwordInput}
        required
      />
      {#if errorMessage}
        <p class="error" role="alert">{errorMessage}</p>
      {/if}
      <button type="submit">Sign in</button>
    </form>
  {:else if status === 'error'}
    <div class="card">
      <p class="error" role="alert">{errorMessage}</p>
      <button type="button" on:click={onRetry}>Retry</button>
      <button type="button" class="ghost" on:click={onSignOut}>Sign out</button>
    </div>
  {:else}
    <div class="bucket">
      <h2>Active <span class="count">({files.active.length})</span></h2>
      {#if files.active.length === 0}
        <p class="muted">No active files.</p>
      {:else}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th>Expires</th>
                <th>ID</th>
                <th class="link-col">Link</th>
              </tr>
            </thead>
            <tbody>
              {#each files.active as item (item.id + '/' + item.name)}
                <tr>
                  <td class="name">{item.name}</td>
                  <td>{formatBytes(item.size)}</td>
                  <td title={formatTimestamp(item.created_at)}>{ageWords(item)}</td>
                  <td title={expiresAbsolute(item)}>{expiresWords(item)}</td>
                  <td class="mono">{item.id}</td>
                  <td class="link-col">
                    <a
                      href={'/admin/' + encodeURIComponent(item.id) + '/' + encodeURIComponent(item.name)}
                      target="_blank"
                      rel="noopener">open</a
                    >
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>

    <div class="bucket">
      <h2>
        Expired <span class="count">({files.expired.length})</span>
        <span class="muted small">— still on disk, public route returns 404</span>
      </h2>
      {#if files.expired.length === 0}
        <p class="muted">No expired files.</p>
      {:else}
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Size</th>
                <th>Uploaded</th>
                <th>Expired</th>
                <th>ID</th>
                <th class="link-col">Link</th>
              </tr>
            </thead>
            <tbody>
              {#each files.expired as item (item.id + '/' + item.name)}
                <tr>
                  <td class="name">{item.name}</td>
                  <td>{formatBytes(item.size)}</td>
                  <td title={formatTimestamp(item.created_at)}>{ageWords(item)}</td>
                  <td title={expiresAbsolute(item)}>{expiresWords(item)}</td>
                  <td class="mono">{item.id}</td>
                  <td class="link-col">
                    <a
                      href={'/admin/' + encodeURIComponent(item.id) + '/' + encodeURIComponent(item.name)}
                      target="_blank"
                      rel="noopener">open</a
                    >
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        </div>
      {/if}
    </div>
  {/if}
</section>

<style>
  .admin {
    max-width: 1100px;
    margin: 0 auto;
    padding: 24px 16px 48px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .admin-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
  }

  .admin-head h1 {
    margin: 0;
    font-size: 22px;
  }

  .head-right {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-width: 480px;
  }

  .login label {
    font-weight: 600;
  }

  .login input[type='password'] {
    width: 100%;
    padding: 8px 10px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--background, transparent);
    color: var(--foreground);
    font: inherit;
  }

  .error {
    color: var(--danger, #c0392b);
    margin: 0;
  }

  .muted {
    color: var(--muted, #888);
  }

  .small {
    font-size: 13px;
    margin-left: 6px;
  }

  button {
    padding: 8px 14px;
    border-radius: 6px;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--foreground);
    cursor: pointer;
    font: inherit;
  }

  button.ghost {
    background: transparent;
  }

  .bucket {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .bucket h2 {
    margin: 0;
    font-size: 16px;
    display: flex;
    align-items: baseline;
    gap: 6px;
  }

  .count {
    color: var(--muted, #888);
    font-weight: normal;
  }

  .table-wrap {
    overflow-x: auto;
    border: 1px solid var(--border);
    border-radius: 8px;
  }

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
  }

  th,
  td {
    padding: 8px 12px;
    text-align: left;
    border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }

  tr:last-child td {
    border-bottom: none;
  }

  th {
    font-weight: 600;
    background: var(--card);
    position: sticky;
    top: 0;
  }

  td.name {
    max-width: 320px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  td.mono,
  .mono {
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px;
  }

  .link-col {
    text-align: right;
  }

  a {
    color: inherit;
  }

  code {
    font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
    background: color-mix(in oklch, var(--card) 80%, transparent);
    padding: 1px 4px;
    border-radius: 4px;
  }
</style>
