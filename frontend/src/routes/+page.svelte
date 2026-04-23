<script lang="ts">
    let buttonState: 'idle' | 'uploading' | 'upload_success' | 'upload_error' | 'copy_success' | 'copy_error' = 'idle';
    let isDragging = false;
    let dragCounter = 0;
    let uploadedFileUrl = '';
    let uploadComplete = false;
    let fileInput: HTMLInputElement;
    let uploadProgress = 0;
    let statusText = '> curl --upload-file hello.txt https://upload.doyun.me/hello.txt';

    function openfile() {
        fileInput.click();
    }

    function onFileSelected(e: Event) {
        const target = e.target as HTMLInputElement;
        if (!target.files || target.files.length === 0) {
            return;
        }
        uploadComplete = false;
        const file = target.files[0];
        uploadFile(file);
    }

    function uploadFile(file: File) {
        buttonState = 'uploading';
        uploadProgress = 0;
        statusText = 'Uploading... (0%)';

        const filename = file.name;
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', `/${filename}`, true);

        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                uploadProgress = Math.round((e.loaded / e.total) * 100);
                statusText = `Uploading... (${uploadProgress}%)`;
            }
        };

        xhr.onload = function() {
            if (xhr.status >= 200 && xhr.status < 300) {
                let url = xhr.responseText;
                url = url.trim().replace(/\u00A0/g, '');
                uploadedFileUrl = url;
                statusText = uploadedFileUrl;
                buttonState = 'upload_success';
                uploadComplete = true;
                uploadProgress = 100;
                setTimeout(() => {
                    buttonState = 'idle';
                }, 500);
            } else {
                statusText = 'Upload failed.';
                buttonState = 'upload_error';
                uploadProgress = 0;
                setTimeout(() => {
                    buttonState = 'idle';
                }, 2000);
            }
        };

        xhr.onerror = function() {
            statusText = 'Upload failed.';
            buttonState = 'upload_error';
            uploadProgress = 0;
            setTimeout(() => {
                buttonState = 'idle';
            }, 2000);
        };

        xhr.send(file);
    }

    function onDragEnter(e: DragEvent) {
        e.preventDefault();
        dragCounter++;
        if (dragCounter === 1) {
            isDragging = true;
        }
    }

    function onDragLeave(e: DragEvent) {
        e.preventDefault();
        dragCounter--;
        if (dragCounter === 0) {
            isDragging = false;
        }
    }

    function onDrop(e: DragEvent) {
        e.preventDefault();
        dragCounter = 0;
        isDragging = false;

        if (!e.dataTransfer || !e.dataTransfer.files) {
            return;
        }

        const files = e.dataTransfer.files;

        if (files.length !== 1) {
            alert("Please drop only one file.");
            return;
        }

        uploadComplete = false;
        const file = files[0];
        uploadFile(file);
    }

    async function copyurl() {
        if (buttonState !== 'idle') return;

        try {
            await navigator.clipboard.writeText(statusText.replace('> ', ''));
            buttonState = 'copy_success';
        } catch (err) {
            console.error('Failed to copy: ', err);
            buttonState = 'copy_error';
        } finally {
            setTimeout(() => {
                buttonState = 'idle';
            }, 1000);
        }
    }

    function formatFileSize(bytes: number): string {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
</script>

<section class="hero">
    <input type="file" bind:this={fileInput} style="display: none" on:change={onFileSelected} />

    <div class="hero-content">
        <p class="hero-label">File share service via curl</p>
        <h1 class="hero-title">Upload Your File</h1>
        <p class="hero-desc">Share files instantly from your terminal or browser</p>
    </div>

    <div class="upload-widget">
        <div class="terminal-bar">
            <div class="terminal-dots">
                <span class="dot dot-red"></span>
                <span class="dot dot-yellow"></span>
                <span class="dot dot-green"></span>
            </div>
            <div class="terminal-content">
                {#if uploadComplete}
                    <a href={statusText} target="_blank" class="terminal-link">{statusText}</a>
                {:else}
                    <span class="terminal-text">{statusText}</span>
                {/if}
            </div>
            <button
                type="button"
                class="btn btn-circle copy-btn"
                on:click={copyurl}
                class:is-success={buttonState === 'copy_success' || buttonState === 'upload_success'}
                class:is-error={buttonState === 'upload_error' || buttonState === 'copy_error'}
            >
                {#if buttonState === 'uploading'}
                    <svg class="icon-spin" width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
                    </svg>
                {:else if buttonState === 'upload_success' || buttonState === 'copy_success'}
                    <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z"/>
                    </svg>
                {:else if buttonState === 'upload_error' || buttonState === 'copy_error'}
                    <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M7.005 3.1a1 1 0 1 1 1.99 0l-.388 6.35a.61.61 0 0 1-1.214 0L7.005 3.1ZM7 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0Z"/>
                    </svg>
                {:else}
                    <svg width="14" height="14" fill="currentColor" viewBox="0 0 16 16">
                        <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"/>
                        <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"/>
                    </svg>
                {/if}
            </button>
        </div>

        {#if buttonState === 'uploading'}
            <div class="progress-bar">
                <div class="progress-fill" style="width: {uploadProgress}%"></div>
            </div>
        {/if}

        <div
            class="drop-zone"
            class:is-dragging={isDragging}
            role="button"
            tabindex="0"
            on:dragenter={onDragEnter}
            on:dragleave={onDragLeave}
            on:drop|preventDefault={onDrop}
            on:dragover|preventDefault
            on:click={openfile}
            on:keydown={(e) => { if (e.key === 'Enter' || e.key === ' ') openfile(); }}
        >
            {#if isDragging}
                <div class="drag-overlay"></div>
            {/if}
            <div class="drop-zone-content">
                <div class="drop-icon">
                    <svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"/>
                    </svg>
                </div>
                <p class="drop-title">Drag a file here</p>
                <p class="drop-sub">or <a href="#upload" on:click|preventDefault={openfile} class="drop-link">browse files</a></p>
            </div>
        </div>
    </div>
</section>

<style>
    .hero {
        padding: 3rem 1.5rem;
        display: flex;
        flex-direction: column;
        align-items: center;
    }

    .hero-content {
        text-align: center;
        margin-bottom: 2.5rem;
    }
    .hero-label {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: var(--color-accent);
        margin: 0 0 0.75rem;
    }
    .hero-title {
        font-size: clamp(2rem, 5vw, 3rem);
        font-weight: 800;
        margin: 0 0 0.5rem;
        letter-spacing: -0.02em;
        background: linear-gradient(135deg, #fff 0%, #a5a5b4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    .hero-desc {
        font-size: 1rem;
        color: var(--color-text-muted);
        margin: 0;
    }

    /* Upload Widget */
    .upload-widget {
        width: 100%;
        max-width: 720px;
    }

    /* Terminal Bar */
    .terminal-bar {
        background-color: var(--color-surface);
        border: 1px solid var(--color-border);
        border-bottom: none;
        border-radius: var(--radius-lg) var(--radius-lg) 0 0;
        padding: 0.75rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.75rem;
    }
    .terminal-dots {
        display: flex;
        gap: 6px;
        flex-shrink: 0;
    }
    .dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
    }
    .dot-red { background-color: #ff5f57; }
    .dot-yellow { background-color: #febc2e; }
    .dot-green { background-color: #28c840; }

    .terminal-content {
        flex: 1;
        min-width: 0;
        overflow: hidden;
    }
    .terminal-text {
        font-family: var(--font-mono);
        font-size: 0.8rem;
        color: var(--color-text-muted);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
    }
    .terminal-link {
        font-family: var(--font-mono);
        font-size: 0.8rem;
        color: var(--color-accent-hover);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        display: block;
        transition: color var(--transition);
    }
    .terminal-link:hover {
        color: var(--color-accent);
    }

    .copy-btn {
        background-color: var(--color-surface-hover);
        border: 1px solid var(--color-border);
        transition: all var(--transition);
    }
    .copy-btn:hover {
        background-color: rgba(255, 255, 255, 0.1);
        box-shadow: none;
    }
    .copy-btn.is-success {
        background-color: var(--color-success);
        border-color: var(--color-success);
    }
    .copy-btn.is-error {
        background-color: var(--color-error);
        border-color: var(--color-error);
    }

    /* Progress */
    .progress-bar {
        height: 3px;
        background-color: var(--color-surface);
        border-left: 1px solid var(--color-border);
        border-right: 1px solid var(--color-border);
    }
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--color-accent), var(--color-accent-hover));
        transition: width 200ms ease;
        border-radius: 0 2px 2px 0;
    }

    /* Drop Zone */
    .drop-zone {
        background-color: var(--color-surface);
        border: 1px solid var(--color-border);
        border-top: 1px dashed rgba(255, 255, 255, 0.08);
        border-radius: 0 0 var(--radius-lg) var(--radius-lg);
        min-height: 260px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        transition: all var(--transition);
        cursor: pointer;
    }
    .drop-zone:hover {
        border-color: rgba(255, 255, 255, 0.12);
        background-color: var(--color-surface-hover);
    }
    .drop-zone.is-dragging {
        border-color: var(--color-accent);
        background-color: var(--color-accent-glow);
    }

    .drag-overlay {
        position: absolute;
        inset: 8px;
        border: 2px dashed var(--color-accent);
        border-radius: var(--radius-md);
        animation: drag-pulse 1.5s ease-in-out infinite;
        pointer-events: none;
    }

    .drop-zone-content {
        text-align: center;
        pointer-events: none;
    }
    .drop-zone-content > * {
        pointer-events: auto;
    }
    .drop-icon {
        color: var(--color-text-dim);
        margin-bottom: 1rem;
    }
    .drop-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: var(--color-text);
        margin: 0 0 0.375rem;
    }
    .drop-sub {
        font-size: 0.875rem;
        color: var(--color-text-muted);
        margin: 0;
    }
    .drop-link {
        color: var(--color-accent-hover);
        font-weight: 500;
        cursor: pointer;
        transition: color var(--transition);
    }
    .drop-link:hover {
        color: var(--color-accent);
    }

    .icon-spin {
        animation: spin 1s linear infinite;
    }

    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    @keyframes drag-pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    @media (max-width: 640px) {
        .hero { padding: 2rem 1rem; }
        .terminal-text, .terminal-link { font-size: 0.7rem; }
    }
</style>
