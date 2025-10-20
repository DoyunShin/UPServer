<script>
    import { page } from '$app/stores';
</script>

<div style="max-width: 960px; margin: 3rem auto; padding: 0 1rem; text-align: center;">
    <div>
        <p>Error</p>
        <h1>{$page.status}</h1>
        <p>{$page.error.message}</p>
    </div>
</div>

<style>
    p:first-child {
        font-weight: bold;
        color: #dc3545;
        margin-bottom: 0.5rem;
    }
    h1 {
        font-weight: bold;
    }
    p:last-child {
        font-weight: bold;
    }
</style>