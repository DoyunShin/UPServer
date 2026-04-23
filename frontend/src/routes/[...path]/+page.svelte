<script lang="ts">
    import DownloadView from "$lib/DownloadView.svelte";
    import { page } from "$app/stores";

    const [fileid, ...filenameParts] = $page.params.path.split("/");
    const filename = filenameParts.join("/");
</script>

<DownloadView fileid={fileid} filename={filename} />
