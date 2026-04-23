<script>
    import { page } from '$app/stores';
</script>

<div class="error-page">
    <div class="error-code">{$page.status}</div>
    <p class="error-msg">{$page.error.message}</p>
    <a href="/" class="btn btn-ghost" style="margin-top: 1.5rem;">Back to Home</a>
</div>

<style>
    .error-page {
        text-align: center;
        padding: 4rem 1.5rem;
    }
    .error-code {
        font-size: 6rem;
        font-weight: 800;
        letter-spacing: -0.04em;
        background: linear-gradient(135deg, var(--color-text-dim) 0%, var(--color-text-muted) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        line-height: 1;
        margin-bottom: 0.5rem;
    }
    .error-msg {
        font-size: 1.125rem;
        color: var(--color-text-muted);
        margin: 0;
    }
</style>
