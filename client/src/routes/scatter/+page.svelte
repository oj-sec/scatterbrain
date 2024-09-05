<script>
    import {
        Stepper,
        Step,
        FileDropzone,
        ListBox,
        ListBoxItem,
        popup,
        getToastStore,
    } from "@skeletonlabs/skeleton";

    // Variables
    let files = null;
    let fileData = "";
    let parsedData = null;
    let previewData = null;
    let selectedEmbeddingField = "";
    let selectedCategoryField = "";
    let embeddingModel = "mixedbread-ai/mxbai-embed-large-v1";
    let selectedDimensionReduction = "PaCMAP";
    let selectedOutputDimensions = "2";
    let selectedColourScheme = "mako";
    let progress = 0;
    let completed = false;
    let progressMessage = "";
    let plotHTML = "";
    const toastStore = getToastStore();

    // Watchers
    $: fileData, parseFileData();
    $: previewData = parsedData ? parsedData.slice(0, 5) : null;

    // Upload handler
    function onFileDrop(e) {
        let file = e.target.files[0];
        console.log("file", file);
        let reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => {
            fileData = reader.result;
        };
    }

    function parseFileData() {
        if (!fileData) return;
        const fileString = atob(fileData.split(",")[1]);
        if (files) {
            let ext = files[0].name.split(".").pop();
            if (ext === "json") {
                parsedData = JSON.parse(fileString);
            } else if (ext === "ndjson") {
                parsedData = fileString
                    .split("\n")
                    .map((line) => JSON.parse(line));
            } else if (ext === "csv") {
                let keys = [];
                let rows = parseCSV(fileString);
                if (rows.length > 0) {
                    keys = rows[0];
                }
                parsedData = rows.slice(1).map((line) => {
                    let obj = {};
                    keys.forEach((key, i) => {
                        obj[key] = line[i]
                            ? line[i].replace(/^"(.*)"$/, "$1")
                            : "";
                    });
                    return obj;
                });
            }
        }
    }

    function parseCSV(fileString) {
        let rows = [];
        let regex = /(?:"([^"]*(?:""[^"]*)*)"|([^",\s]+)|)(?=\s*,|\s*$)/g;
        let currentRow = [];
        let match;
        let insideQuotes = false;
        let buffer = "";

        for (let i = 0; i < fileString.length; i++) {
            let char = fileString[i];

            if (insideQuotes) {
                if (char === '"' && fileString[i + 1] === '"') {
                    buffer += '"';
                    i++;
                } else if (char === '"') {
                    insideQuotes = false;
                } else {
                    buffer += char;
                }
            } else {
                if (char === '"') {
                    insideQuotes = true;
                } else if (char === ",") {
                    currentRow.push(buffer.trim());
                    buffer = "";
                } else if (char === "\n" || i === fileString.length - 1) {
                    if (i === fileString.length - 1) {
                        buffer += char;
                    }
                    currentRow.push(buffer.trim());
                    rows.push(currentRow);
                    currentRow = [];
                    buffer = "";
                } else {
                    buffer += char;
                }
            }
        }
        return rows;
    }

    function clear() {
        files = null;
        fileData = "";
        parsedData = null;
    }

    function viewAll() {
        previewData = parsedData;
    }

    // Server communications
    async function generateEmbeddings() {
        progressMessage = "Initialising state";
        const resetResponse = await fetch("/api/reset", {
            method: "GET",
        });

        progress = 0;

        const setModelResponse = await fetch("/api/set-model", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                model: embeddingModel,
                dimensions: 512,
            }),
        });

        const modelExists = await fetch("/api/check-model", {
            method: "GET",
        });
        let modelExistsData = await modelExists.json();

        if (modelExistsData.status === false) {
            progressMessage =
                "Model not in cache - downloading. This may take a few minutes...";
            const downloadModel = await fetch("/api/download-model", {
                method: "GET",
            });
            const downloadModelData = await downloadModel.json();
            if (downloadModelData.status === false) {
                progressMessage = "Model download failed";
                return;
            } else {
                progressMessage = "Model downloaded";
            }
        }

        for (const row of parsedData) {
            const embedResponse = await fetch("/api/embed-text", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    row: row,
                    field: selectedEmbeddingField,
                }),
            });
            const embedResponseData = await embedResponse.json();
            console.log(embedResponseData);
            if (embedResponseData.status === "error") {
                toastStore.trigger({
                    background: "variant-filled-error",
                    message: "Error embedding text",
                });
                progressMessage = "Error embedding text. Please try again.";
                return;
            } else {
                progress++;
                progressMessage = `Embedding document ${progress} of ${parsedData.length}`;
            }
        }

        progressMessage =
            "Projecting embeddings. This may take a few minutes on large datasets...";
        const dimResponse = await fetch("/api/reduce-dims", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                plotDimensions: selectedOutputDimensions,
            }),
        });

        progressMessage = "Generating plot";
        const plotResponse = await fetch("/api/plot", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                field: selectedEmbeddingField,
                cmap: selectedColourScheme,
                category: selectedCategoryField,
            }),
        });

        const plotResponseData = await plotResponse.json();
        if (plotResponseData.status === "error") {
            toastStore.trigger({
                background: "variant-filled-error",
                message: "Error generating plot",
            });
            progressMessage = "Error generating plot";
            return;
        } else {
            progressMessage = "Completed";
            plotHTML = plotResponseData.plot;
            completed = true;
        }
    }

    function onCompleteHandler() {
        console.log("opening new tab");
        const newTab = window.open();
        newTab.document.write(plotHTML);
        newTab.document.close();
        console.log("completed");
    }

    function onNextHandler() {
        progressMessage = "";
        progress = 0;
    }

    // Popups
    const popupCombobox = {
        event: "click",
        target: "popupCombobox",
        placement: "bottom",
        closeQuery: ".listbox-item",
    };
    const popupCombobox1 = {
        event: "click",
        target: "popupCombobox1",
        placement: "bottom",
        closeQuery: ".listbox-item",
    };
</script>

<div class="container h-full mx-auto flex justify-center items-center">
    <div class="card p-4 m-4">
        <Stepper
            buttonCompleteLabel="View plot"
            on:complete={onCompleteHandler}
            on:next={onNextHandler}
        >
            <Step locked={!files}>
                <svelte:fragment slot="header">Load data</svelte:fragment>
                <div
                    class="min-h-[450px] min-w-[800px] items-center justify-center max-w-screen-lg m-auto overflow-scroll"
                >
                    <FileDropzone
                        name="files"
                        on:change={onFileDrop}
                        bind:files
                        accept=".json, .ndjson, .txt, .csv"
                        class="w-4/5 m-auto"
                    >
                        <svelte:fragment slot="lead">
                            {#if files}
                                <i
                                    class="fa-solid fa-file-circle-check text-4xl"
                                ></i>
                            {:else}
                                <i class="fa-solid fa-file-arrow-up text-4xl" />
                            {/if}
                        </svelte:fragment>
                        <svelte:fragment slot="message">
                            {#if files}
                                {files[0].name}
                            {:else}
                                <b>Click to upload</b> or drag & drop
                            {/if}
                        </svelte:fragment>
                        <svelte:fragment slot="meta">
                            {#if files}
                                {files[0].size} bytes
                            {:else}
                                <b>.json, .ndjson and .csv allowed</b>
                            {/if}
                        </svelte:fragment>
                    </FileDropzone>
                    <div class="m-4">
                        <span class="flex justify-between items-center">
                            <h3 class="h5">File content</h3>
                            <span>
                                <button
                                    class="btn variant-filled"
                                    disabled={!files}
                                    on:click={viewAll}
                                >
                                    View all
                                </button>
                                <button
                                    class="btn variant-filled m-2"
                                    disabled={!files}
                                    on:click={clear}
                                >
                                    Clear
                                </button>
                            </span>
                        </span>
                        {#if previewData}
                            <div class="table-container">
                                <table class="table table-hover">
                                    <thead>
                                        <tr>
                                            {#each Object.keys(previewData[0]) as header}
                                                <th>{header}</th>
                                            {/each}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {#each previewData as row}
                                            <tr>
                                                {#each Object.values(row) as value}
                                                    <td>{value ? value : ""}</td
                                                    >
                                                {/each}
                                            </tr>
                                        {/each}
                                    </tbody>
                                    <tfoot>
                                        <tr>
                                            <td
                                                colspan={Object.keys(
                                                    previewData[0],
                                                ).length}
                                                class="text-right normal-case"
                                            >
                                                Parsed a total of {parsedData.length}
                                                rows
                                            </td>
                                        </tr>
                                    </tfoot>
                                </table>
                            </div>
                        {:else}
                            <div
                                class="card p-4 m-4 text-center h-full w-ful justify-center"
                            >
                                <p>Upload a file to preview data</p>
                            </div>
                        {/if}
                    </div>
                </div>
            </Step>
            <Step locked={!selectedEmbeddingField}>
                <svelte:fragment slot="header">Configure</svelte:fragment>
                <div class="min-h-[450px] min-w-[800px]">
                    <div class="grid grid-cols-2 gap-4">
                        <label class="label">
                            <span class="ml-2">Embedding field</span>
                            <button
                                type="button"
                                class="btn m-2 variant-filled justify-between w-full"
                                use:popup={popupCombobox}
                            >
                                {selectedEmbeddingField
                                    ? selectedEmbeddingField
                                    : "Embedding field"}
                                <i class="fa-solid fa-caret-down"></i>
                            </button>
                        </label>
                        <div
                            class="card w-48 shadow-xl py-2 z-50"
                            data-popup="popupCombobox"
                        >
                            <ListBox
                                rounded="rounded-none"
                                active="variant-ghost"
                            >
                                {#each Object.keys(previewData[0]) as field}
                                    <ListBoxItem
                                        name="medium"
                                        on:click={() => {
                                            selectedEmbeddingField = field;
                                        }}
                                    >
                                        {field}
                                    </ListBoxItem>
                                {/each}
                            </ListBox>
                        </div>
                        <label class="label">
                            <span class="ml-2"
                                >Category field <i class="text-gray-600 m-1"
                                    >(Optional)</i
                                ></span
                            >
                            <button
                                type="button"
                                class="btn m-2 variant-ghost justify-between w-full"
                                use:popup={popupCombobox1}
                            >
                                {selectedCategoryField
                                    ? selectedCategoryField
                                    : "Category field"}
                                <i class="fa-solid fa-caret-down"></i>
                            </button>
                        </label>
                        <div
                            class="card w-48 shadow-xl py-2 z-50"
                            data-popup="popupCombobox1"
                        >
                            <ListBox
                                rounded="rounded-none"
                                active="variant-ghost"
                            >
                                {#each Object.keys(previewData[0]) as field}
                                    <ListBoxItem
                                        name="medium"
                                        on:click={() => {
                                            selectedCategoryField = field;
                                        }}
                                    >
                                        {field}
                                    </ListBoxItem>
                                {/each}
                            </ListBox>
                        </div>
                        <label class="label">
                            <span class="ml-2">Embedding model</span>
                            <input
                                type="text"
                                class="input rounded-full m-2"
                                placeholder="Embedding model"
                                bind:value={embeddingModel}
                            />
                        </label>
                        <label class="label">
                            <span class="ml-2">Dimension reduction</span>
                            <select
                                class="select rounded-full m-2"
                                bind:value={selectedDimensionReduction}
                            >
                                <option value="PaCMAP">PaCMAP</option>
                            </select>
                        </label>
                        <label class="label">
                            <span class="ml-2">Output dimensions</span>
                            <select
                                class="select rounded-full m-2"
                                bind:value={selectedOutputDimensions}
                            >
                                <option value="2"> 2</option>
                                <option value="3"> 3</option>
                            </select>
                        </label>
                        <label class="label">
                            <span class="ml-2">Colour scheme</span>
                            <select
                                class="select rounded-full m-2"
                                bind:value={selectedColourScheme}
                            >
                                <option value="mako">🔵 mako</option>
                                <option value="rocket">🔴 rocket</option>
                                <option value="flare">🟣 flare</option>
                                <option value="magma">🟠 magma</option>
                                <option value="viridis">🟢 viridis</option>
                            </select>
                        </label>
                    </div>
                </div></Step
            >
            <Step locked={!completed}>
                <svelte:fragment slot="header"
                    >Generate embeddings</svelte:fragment
                >
                <div
                    class="min-h-[450px] min-w-[800px] flex flex-col items-center justify-center"
                >
                    <progress
                        class="m-4"
                        value={progress}
                        max={parsedData.length}
                    />
                    {#if progressMessage}
                        <i class="text-center">
                            {progressMessage}
                        </i>
                    {/if}
                    <button
                        class="btn variant-filled mt-4"
                        disabled={progress === parsedData.length}
                        on:click={generateEmbeddings}
                    >
                        Generate embeddings
                    </button>
                </div>
            </Step>
        </Stepper>
    </div>
</div>
