<script lang="ts">
    import DownloadView from "$lib/DownloadView.svelte";
    import { page } from "$app/stores";

    const [fileid, ...filenameParts] = $page.params.path.split("/");
    const filename = filenameParts.join("/");
</script>

<div style="max-width: 960px; margin: 3rem auto; padding: 0 1rem; text-align: center;">
    <DownloadView fileid={fileid} filename={filename} />
</div>
