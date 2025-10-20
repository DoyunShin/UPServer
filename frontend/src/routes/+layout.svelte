<script>
    import { onMount } from 'svelte';
    import '../global.css';

    export const ssr = false;
    let info = null;

    onMount(async () => {
        try {
            const res = await fetch('/info');
            if (res.ok) {
                info = await res.json();
                if (info && document) {
                    document.title = info.name;
                }
            }
        } catch (e) {
            console.error("Failed to fetch /info", e);
        }
    });
</script>

<svelte:head>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Inter:300italic,400italic,600italic,700italic,800italic,400,300,600,700,800&amp;display=swap">
  <style>
    .page-wrapper {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
      color: #fff;
      font-family: 'Inter', sans-serif;
    }
    ::selection {
      background-color: #007bff;
      color: #fff;
    }

  </style>
</svelte:head>

<div class="page-wrapper">
<nav>
    <div>
        <a href="/">
            <img style="height: 2em;width: 2em;margin-right: 0.5em;" src={info ? info.icon : '/assets/img/favicon.svg'} alt="icon">
            <span style="font-size: 1.2em; font-weight: bold;">{info ? info.name : 'ServerName'}</span>
        </a>
        <div id="navcol-1">
            <ul>
                <li><a href="/">Home</a></li>
                <li hidden><a href="/pricing">Pricing</a></li>
                <li><a href={info ? info.contact : '/contacts'}>Contacts</a></li>
            </ul>
        </div>
    </div>
</nav>

<main>
    <slot />
</main>

<footer>
    <div>
        {#if info}
            <div>
                {#each info.webinfo as column}
                    <div>
                        <h3>{column[0]}</h3>
                        <ul>
                            {#each column.slice(1) as link}
                                <li><a href={link[1]}>{link[0]}</a></li>
                            {/each}
                        </ul>
                    </div>
                {/each}
                <div>
                    <div style="display: flex; align-items: center;">
                        <img style="height: 2em;width: 2em;margin-right: 0.5em;" src={info.icon} alt="icon">
                        <span>{info.brand}</span>
                    </div>
                    <p>{@html info.info}</p>
                </div>
            </div>
            <hr>
            <div>
                <p>Copyright © {new Date().getFullYear()} DoyunShin</p>
                <ul>
                    <li>
                        <a href="https://doyun.me">
                            <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM13 7.207V13.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V7.207l5-5z"/>
                            </svg>
                        </a>
                    </li>
                    <li>
                        <a href="//github.com/DoyunShin">
                            <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>
                            </svg>
                        </a>
                    </li>
                    <li>
                        <a href="//twitter.com/@cm1320">
                            <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865z"/>
                            </svg>
                        </a>
                    </li>
                </ul>
            </div>
        {:else}
            <div>
                <div>
                    <h3>Services</h3>
                    <ul>
                        <li><a href="#">Loading...</a></li>
                    </ul>
                </div>
                <div>
                    <h3>About</h3>
                    <ul>
                        <li><a href="#">Loading...</a></li>
                    </ul>
                </div>
                <div>
                    <h3>ORY Services</h3>
                    <ul>
                        <li><a href="#">Loading...</a></li>
                    </ul>
                </div>
                <div>
                    <div style="display: flex; align-items: center;">
                        <img style="height: 2em;width: 2em;margin-right: 0.5em;" src="/assets/img/favicon.svg" alt="icon">
                        <span>Loading...</span>
                    </div>
                    <p>Loading...</p>
                </div>
            </div>
            <hr>
            <div>
                <p>Copyright © {new Date().getFullYear()} DoyunShin</p>
                <ul>
                    <li>
                        <a href="https://doyun.me">
                            <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M8.707 1.5a1 1 0 0 0-1.414 0L.646 8.146a.5.5 0 0 0 .708.708L2 8.207V13.5A1.5 1.5 0 0 0 3.5 15h9a1.5 1.5 0 0 0 1.5-1.5V8.207l.646.647a.5.5 0 0 0 .708-.708L13 5.793V2.5a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5v1.293zM13 7.207V13.5a.5.5 0 0 1-.5.5h-9a.5.5 0 0 1-.5-.5V7.207l5-5z"/>
                            </svg>
                        </a>
                    </li>
                    <li>
                        <a href="//github.com/DoyunShin">
                            <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8"/>
                            </svg>
                        </a>
                    </li>
                    <li>
                        <a href="//twitter.com/@cm1320">
                            <svg xmlns="http://www.w3.org/2000/svg" width="1.2em" height="1.2em" fill="currentColor" viewBox="0 0 16 16">
                                <path d="M12.6.75h2.454l-5.36 6.142L16 15.25h-4.937l-3.867-5.07-4.425 5.07H.316l5.733-6.57L0 .75h5.063l3.495 4.633L12.601.75Zm-.86 13.028h1.36L4.323 2.145H2.865z"/>
                            </svg>
                        </a>
                    </li>
                </ul>
            </div>
        {/if}
    </div>
</footer>
</div>

<style>
    nav {
        background-color: #212529;
        padding: 1rem 0;
        position: sticky;
        top: 0;
        z-index: 1020;
    }
    nav > div {
        display: flex;
        justify-content: space-between;
        align-items: center;
        max-width: 960px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    nav a {
        color: white;
        text-decoration: none;
        display: flex;
        align-items: center;
    }
    nav ul {
        display: flex;
        list-style: none;
        margin: 0;
        padding: 0;
    }
    nav ul li {
        margin-left: 1rem;
    }
    footer {
        background-color: #212529;
        padding: 0.5rem 0;
        width: 100%;
    }
    footer > div {
        display: flex;
        flex-direction: column;
        max-width: 960px;
        margin: 0 auto;
        padding: 0 1rem;
    }
    footer > div > div:first-child {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
    }
    footer h3 {
        font-size: 1rem;
        font-weight: bold;
        margin-top: 10px;
    }
    footer ul {
        list-style: none;
        padding: 0;
    }
    footer a {
        color: #6c757d;
        text-decoration: none;
    }
    footer > div > div:first-child ul li {
        margin-bottom: 0.25rem;
    }

    footer > div > div:first-child > div:last-child > div:first-child span {
        font-weight: bold;
    }
    footer hr {
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        border: 0;
        border-top: 1px solid rgba(255, 255, 255, 0.1);
    }
    footer > div > div:last-child {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-top: 0.5rem;
        color: #6c757d;
    }
    footer > div > div:last-child ul {
        display: flex;
        list-style: none;
        padding: 0;
        margin: 0;
    }
    footer > div > div:last-child ul li {
        margin-left: 1rem;
    }
    main {
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
        padding-bottom: 5vh;
    }
</style>