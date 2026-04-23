<script>
    import { onMount } from 'svelte';
    import '../global.css';

    let info = null;

    onMount(async () => {
        try {
            const res = await fetch('/api/info');
            if (res.ok) {
                const body = await res.json();
                info = body.data;
                if (info && document) {
                    document.title = info.name;
                }
            }
        } catch (e) {
            console.error("Failed to fetch /api/info", e);
        }
    });
</script>

<svelte:head>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous">
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap">
</svelte:head>

<div class="page-wrapper">
    <nav>
        <div class="nav-inner">
            <a href="/" class="nav-brand">
                <img src={info ? info.icon : '/assets/img/favicon.svg'} alt="icon" class="nav-icon">
                <span>{info ? info.name : 'UPServer'}</span>
            </a>
            <div class="nav-links">
                <a href="/" class="nav-link">Home</a>
                <a href={info ? info.contact : '/contacts'} class="nav-link">Contacts</a>
            </div>
        </div>
    </nav>

    <main>
        <slot />
    </main>

    <footer>
        <div class="footer-inner">
            {#if info}
                <div class="footer-columns">
                    {#each info.webinfo as column}
                        <div class="footer-col">
                            <h3>{column[0]}</h3>
                            <ul>
                                {#each column.slice(1) as link}
                                    <li><a href={link[1]}>{link[0]}</a></li>
                                {/each}
                            </ul>
                        </div>
                    {/each}
                    <div class="footer-col footer-brand">
                        <div class="footer-brand-row">
                            <img src={info.icon} alt="icon" class="footer-icon">
                            <span>{info.brand}</span>
                        </div>
                        <p>{@html info.info}</p>
                    </div>
                </div>
            {:else}
                <div class="footer-columns">
                    <div class="footer-col">
                        <h3>Loading...</h3>
                    </div>
                </div>
            {/if}
            <div class="footer-divider"></div>
            <div class="footer-bottom">
                <p>Copyright &copy; {new Date().getFullYear()} DoyunShin</p>
                <div class="footer-socials">
                    <a href="https://doyun.me" aria-label="Homepage">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM13 7.207V13.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V7.207l5-5z"/>
                        </svg>
                    </a>
                    <a href="//github.com/DoyunShin" aria-label="GitHub">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>
                        </svg>
                    </a>
                    <a href="//twitter.com/@cm1320" aria-label="X (Twitter)">
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865z"/>
                        </svg>
                    </a>
                </div>
            </div>
        </div>
    </footer>
</div>

<style>
    .page-wrapper {
        display: flex;
        flex-direction: column;
        min-height: 100vh;
    }

    /* Nav */
    nav {
        background-color: rgba(15, 15, 19, 0.8);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border-bottom: 1px solid var(--color-border);
        position: sticky;
        top: 0;
        z-index: 1020;
    }
    .nav-inner {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 1080px;
        margin: 0 auto;
        padding: 0.875rem 1.5rem;
    }
    .nav-brand {
        display: flex;
        align-items: center;
        gap: 0.625rem;
        font-weight: 700;
        font-size: 1.1rem;
        color: var(--color-text);
        transition: opacity var(--transition);
    }
    .nav-brand:hover {
        opacity: 0.8;
    }
    .nav-icon {
        height: 1.75rem;
        width: 1.75rem;
        border-radius: var(--radius-sm);
    }
    .nav-links {
        display: flex;
        gap: 0.25rem;
    }
    .nav-link {
        padding: 0.5rem 1rem;
        border-radius: var(--radius-md);
        font-size: 0.875rem;
        font-weight: 500;
        color: var(--color-text-muted);
        transition: all var(--transition);
    }
    .nav-link:hover {
        color: var(--color-text);
        background-color: var(--color-surface-hover);
    }

    /* Main */
    main {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    /* Footer */
    footer {
        background-color: var(--color-surface);
        border-top: 1px solid var(--color-border);
        margin-top: auto;
    }
    .footer-inner {
        max-width: 1080px;
        margin: 0 auto;
        padding: 2.5rem 1.5rem 1.5rem;
    }
    .footer-columns {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 2rem;
    }
    .footer-col h3 {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-text-muted);
        margin: 0 0 0.75rem;
    }
    .footer-col ul {
        list-style: none;
        padding: 0;
        margin: 0;
    }
    .footer-col ul li {
        margin-bottom: 0.375rem;
    }
    .footer-col a {
        font-size: 0.875rem;
        color: var(--color-text-dim);
        transition: color var(--transition);
    }
    .footer-col a:hover {
        color: var(--color-text);
    }
    .footer-brand-row {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .footer-brand-row span {
        font-weight: 600;
        font-size: 0.9rem;
    }
    .footer-icon {
        height: 1.5rem;
        width: 1.5rem;
        border-radius: var(--radius-sm);
    }
    .footer-brand p {
        font-size: 0.8rem;
        color: var(--color-text-dim);
        margin: 0;
        line-height: 1.5;
    }
    .footer-divider {
        height: 1px;
        background: var(--color-border);
        margin: 1.5rem 0 1rem;
    }
    .footer-bottom {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .footer-bottom p {
        font-size: 0.8rem;
        color: var(--color-text-dim);
        margin: 0;
    }
    .footer-socials {
        display: flex;
        gap: 0.75rem;
    }
    .footer-socials a {
        color: var(--color-text-dim);
        transition: color var(--transition);
        display: flex;
    }
    .footer-socials a:hover {
        color: var(--color-text);
    }

    @media (max-width: 640px) {
        .footer-columns {
            grid-template-columns: repeat(2, 1fr);
        }
        .footer-bottom {
            flex-direction: column;
            gap: 0.75rem;
            text-align: center;
        }
    }
</style>
