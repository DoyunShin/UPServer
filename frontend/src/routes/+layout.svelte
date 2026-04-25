<script lang="ts">
  import '../app.css';
  import { onMount } from 'svelte';
  import Nav from '$lib/components/Nav.svelte';
  import Footer from '$lib/components/Footer.svelte';
  import { ensureInfo, info } from '$lib/stores/info';

  onMount(() => {
    ensureInfo();
  });

  $: if ($info.data?.name && typeof document !== 'undefined') {
    document.title = $info.data.name;
  }
</script>

<div class="app-shell">
  <Nav />
  <main>
    <slot />
  </main>
  <Footer />
</div>
