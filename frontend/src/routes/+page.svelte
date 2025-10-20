<script lang="ts">
    // declare function copyurl(): void;

    let buttonState: 'idle' | 'uploading' | 'upload_success' | 'upload_error' | 'copy_success' | 'copy_error' = 'idle';
    let isDragging = false;
    let dragCounter = 0;
    let uploadStatus: 'idle' | 'uploading' | 'success' | 'error' = 'idle';
    let uploadedFileUrl = '';
    let copySuccessState: 'idle' | 'success' | 'error' = 'idle';
    let uploadComplete = false;
    let fileInput: HTMLInputElement;
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
        statusText = 'Uploading... (0%)';

        const filename = file.name;
        const xhr = new XMLHttpRequest();
        xhr.open('PUT', `/${filename}`, true);

        xhr.upload.onprogress = function(e) {
            if (e.lengthComputable) {
                const percentComplete = Math.round((e.loaded / e.total) * 100);
                statusText = `Uploading... (${percentComplete}%)`;
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
                setTimeout(() => {
                    buttonState = 'idle';
                }, 500);
            } else {
                statusText = 'Upload failed.';
                buttonState = 'upload_error';
                setTimeout(() => {
                    buttonState = 'idle';
                }, 2000);
            }
        };

        xhr.onerror = function() {
            statusText = 'Upload failed.';
            buttonState = 'upload_error';
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
</script>

<header>
    <input type="file" bind:this={fileInput} style="display: none" on:change={onFileSelected} />
    <div>
        <div>
            <div>
                <div style="text-align: center;">
                    <p>File share service via curl</p>
                    <h1>Upload Your File!</h1>
                </div>
            </div>
            <div>
                <div>
                    <div class="upload-widget">
                        <div class="command-line-box">
                            {#if uploadComplete}
                                <a id="status" href={statusText} target="_blank" style="font-family: monospace; color: #888;">{statusText}</a>
                            {:else}
                                <span id="status" style="font-family: monospace;">{statusText}</span>
                            {/if}
                                                    <button id="urlcopy" type="button" on:click={copyurl}
                                class:copy-success={buttonState === 'copy_success' || buttonState === 'upload_success'}
                                style="margin-left: 10px; border-radius: 50%; width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; padding: 0;">
                            
                                                        {#if buttonState === 'uploading'}
                                                            <svg style="animation: spin 1s linear infinite;" width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg" fill="currentColor">
                                                                <path d="M8 3a5 5 0 1 0 4.546 2.914.5.5 0 0 1 .908-.417A6 6 0 1 1 8 2v1z"/>
                                                            </svg>
                                                        {:else if buttonState === 'upload_success' || buttonState === 'copy_success'}
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" id="urlcopysuccessicon">
                                                                <path d="M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z"></path>
                                                            </svg>
                                                        {:else if buttonState === 'upload_error' || buttonState === 'copy_error'}
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" id="urlcopyerroricon">
                                                                <path d="M7.005 3.1a1 1 0 1 1 1.99 0l-.388 6.35a.61.61 0 0 1-1.214 0L7.005 3.1ZM7 12a1 1 0 1 1 2 0 1 1 0 0 1-2 0Z"></path>
                                                            </svg>
                                                        {:else}
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" viewBox="0 0 16 16" id="urlcopyicon">
                                                                <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1v-1z"></path>
                                                                <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5h3zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0h-3z"></path>
                                                            </svg>
                                                        {/if}
                                                    </button>                        </div>
                        <div id="drag-n-drop"
                            on:dragenter={onDragEnter}
                            on:dragleave={onDragLeave}
                            on:drop|preventDefault={onDrop}
                            on:dragover|preventDefault
                        >
                            {#if isDragging}
                                <div class="drag-feedback"></div>
                            {/if}
                            <div style="text-align: center;">
                                <h1>Drag a file here</h1><a id="openfile" href="#" on:click|preventDefault={openfile} style="color: #d3d3d3; text-decoration: none;">or click here</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</header>

<style>
    .upload-widget {
        width: 80%;
        max-width: 960px;
        margin: 40px auto 0;
    }
    .command-line-box {
        background-color: black;
        color: white;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem 0.5rem 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 1.1rem;
    }
    header {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div > div > div > p {
        font-weight: bold;
        color: #19f5aa;
        margin-bottom: 0.5rem;
    }
    h1 {
        font-weight: bold;
        font-size: 2.5rem;
    }
    #drag-n-drop {
        background: #4E4C5C;
        border-radius: 0 0 15px 15px;
        min-height: 300px;
        transition: all ease 0.2s 0s;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .drag-feedback {
        position: absolute;
        top: 10px;
        left: 10px;
        right: 10px;
        bottom: 10px;
        border: 2px dashed #fff;
        border-radius: 10px;
        animation: pulse 1.5s ease-in-out infinite;
    }

    @keyframes pulse {
        0% {
            transform: scale(1);
        }
        50% {
            transform: scale(0.975);
        }
        100% {
            transform: scale(1);
        }
    }
    button {
        background-color: #3763f4;
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
        cursor: pointer;
    }

    #urlcopy.copy-success {
        background-color: #198754; /* green */
        transition: background-color 0.2s ease-in-out;
    }

    @keyframes spin {
        from {
            transform: rotate(0deg);
        }
        to {
            transform: rotate(360deg);
        }
    }
</style>