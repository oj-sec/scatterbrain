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
    import { parseCSV } from "$lib/parsers.js";

    // Variables
    let files = null;
    let fileData = "";
    let parsedData = null;
    let previewData = null;
    let categoryFiles = null;
    let categoryFileData = "";
    let parsedCategoryData = [];
    let detectedFileType = "";
    let inputPrefix = "";
    let categoryPrefix =
        "Represent this sentence for searching relevant passages: ";
    let selectedEmbeddingField = "";
    let embeddingModel = "mixedbread-ai/mxbai-embed-large-v1";
    let progress = 0;
    let max;
    let completed = false;
    let progressMessage = "";
    const toastStore = getToastStore();

    // Watchers
    $: fileData, parseFileData();
    $: previewData = parsedData ? parsedData.slice(0, 5) : null;
    $: categoryFileData, parseCategoryFileData();

    // Upload handler
    function onFileDrop(e) {
        let file = e.target.files[0];
        console.log("file", file);
        let reader = new FileReader();
        reader.readAsText(file, "UTF-8");
        reader.onload = () => {
            fileData = reader.result;
        };
    }

    function onCategoryFileDrop(e) {
        let file = e.target.files[0];
        categoryFiles = e.target.files;
        console.log("file", file);
        let reader = new FileReader();
        reader.readAsText(file, "UTF-8");
        reader.onload = () => {
            categoryFileData = reader.result;
        };
    }

    // Parse file data
    function parseFileData() {
        if (!fileData) return;
        //const fileString = atob(fileData.split(",")[1]);
        const fileString = fileData;
        if (files) {
            let ext = files[0].name.split(".").pop();
            if (ext === "json") {
                detectedFileType = "json";
                parsedData = JSON.parse(fileString);
            } else if (ext === "ndjson") {
                detectedFileType = "ndjson";
                parsedData = fileString
                    .split("\n")
                    .map((line) => JSON.parse(line));
            } else if (ext === "csv") {
                detectedFileType = "csv";
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

    function parseCategoryFileData() {
        if (!categoryFileData) return;
        //const fileString = atob(categoryFileData.split(",")[1]);
        const fileString = categoryFileData;
        parsedCategoryData = fileString
            .split("\n")
            .filter((row) => row.trim() !== "");
        console.log("parsedCategoryData", parsedCategoryData);
    }

    // Helpers
    function clear() {
        files = null;
        fileData = "";
        parsedData = null;
        previewData = null;
        categoryFiles = null;
        categoryFileData = "";
        parsedCategoryData = null;
        inputPrefix = "";
        categoryPrefix = "";
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
        max = parsedCategoryData.length + parsedData.length;

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

        progressMessage = "Generating category embeddings...";
        for (let i = 0; i < parsedCategoryData.length; i++) {
            let data = parsedCategoryData[i];
            let response = await fetch("/api/embed-category", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    text: categoryPrefix + data,
                }),
            });
            let result = await response.json();
            progress++;
            progressMessage = `Generating category embedding ${i + 1} of ${parsedCategoryData.length}`;
        }

        progressMessage = "Categorising input data...";
        for (let i = 0; i < parsedData.length; i++) {
            let data = parsedData[i];
            let response = await fetch("/api/categorise", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    text: inputPrefix + data[selectedEmbeddingField],
                }),
            });
            let result = await response.json();
            parsedData[i].category = result.closest.replace(categoryPrefix, "");
            progress++;
            progressMessage = `Categorising input data ${i + 1} of ${parsedData.length}`;
        }
        completed = true;
        return;
    }

    function createDownloadLink(content, mimeType, filename) {
        let blob = new Blob([content], { type: mimeType });
        let url = URL.createObjectURL(blob);
        let a = document.createElement("a");
        a.href = url;
        a.download = filename;
        a.click();
    }

    function processData(data) {
        return data.map((row) => ({
            ...row,
            category: row.category ? row.category : "",
        }));
    }

    function escapeCsvValue(value) {
        if (typeof value === "string") {
            if (value.includes('"')) {
                value = value.replace(/"/g, '""');
            }
            if (
                value.includes(",") ||
                value.includes('"') ||
                value.includes("\n")
            ) {
                value = `"${value}"`;
            }
        }
        return value;
    }

    function onCompleteHandler() {
        console.log("completed");
        let data = processData(parsedData);
        if (detectedFileType === "json") {
            let json = JSON.stringify(data, null, 2);
            createDownloadLink(json, "application/json", "categorised.json");
        } else if (detectedFileType === "ndjson") {
            let ndjson = data.map((row) => JSON.stringify(row)).join("\n");
            createDownloadLink(
                ndjson,
                "application/json",
                "categorised.ndjson",
            );
        } else if (detectedFileType === "csv") {
            let keys = Object.keys(data[0]);
            let csv =
                keys.join(",") +
                "\n" +
                data
                    .map((row) =>
                        keys.map((key) => escapeCsvValue(row[key])).join(","),
                    )
                    .join("\n");
            createDownloadLink(csv, "text/csv", "categorised.csv");
        } else {
            console.log("Unknown file type");
        }
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
            buttonCompleteLabel="Download file"
            on:complete={onCompleteHandler}
            on:next={onNextHandler}
        >
            <Step locked={!files || !categoryFiles}>
                <svelte:fragment slot="header">Load data</svelte:fragment>
                <div
                    class="min-h-[450px] min-w-[800px] items-center justify-center max-w-screen-lg m-auto overflow-scroll"
                >
                    <div class="grid grid-cols-2 gap-4">
                        <FileDropzone
                            name="files"
                            on:change={onFileDrop}
                            bind:files
                            accept=".json, .ndjson, .txt, .csv"
                            class="m-auto"
                        >
                            <svelte:fragment slot="lead">
                                {#if files}
                                    <i
                                        class="fa-solid fa-file-circle-check text-4xl"
                                    ></i>
                                {:else}
                                    <i
                                        class="fa-solid fa-file-arrow-up text-4xl"
                                    />
                                {/if}
                            </svelte:fragment>
                            <svelte:fragment slot="message">
                                {#if files}
                                    {files[0].name}
                                {:else}
                                    <b>Upload input data</b>
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
                        <FileDropzone
                            name="categoryFiles"
                            on:change={onCategoryFileDrop}
                            bind:categoryFiles
                            accept=".txt, .csv"
                            class="m-auto"
                        >
                            <svelte:fragment slot="lead">
                                {#if categoryFiles}
                                    <i
                                        class="fa-solid fa-file-circle-check text-4xl"
                                    ></i>
                                {:else}
                                    <i
                                        class="fa-solid fa-file-arrow-up text-4xl"
                                    />
                                {/if}
                            </svelte:fragment>
                            <svelte:fragment slot="message">
                                {#if categoryFiles}
                                    {categoryFiles[0].name}
                                {:else}
                                    <b>Upload classification categories</b>
                                {/if}
                            </svelte:fragment>
                            <svelte:fragment slot="meta">
                                {#if categoryFiles}
                                    {categoryFiles[0].size} bytes
                                {:else}
                                    <b>newline-delimited text file allowed</b>
                                {/if}
                            </svelte:fragment>
                        </FileDropzone>
                    </div>
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
                                                {#if parsedCategoryData.length > 0}
                                                    and {parsedCategoryData.length}
                                                    categories
                                                {/if}
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
                                        class="truncate"
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
                            <span class="ml-2">Embedding model</span>
                            <input
                                type="text"
                                class="input rounded-full m-2"
                                placeholder="Embedding model"
                                bind:value={embeddingModel}
                            />
                        </label>
                        <label class="label">
                            <span class="ml-2">Category prefix</span>
                            <textarea
                                type="textarea"
                                class="input rounded m-2"
                                placeholder="Category prefix"
                                bind:value={categoryPrefix}
                            />
                        </label>
                        <label class="label">
                            <span class="ml-2">Input prefix</span>
                            <textarea
                                type="textarea"
                                class="input rounded m-2"
                                placeholder="Input prefix"
                                bind:value={inputPrefix}
                            />
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
                    <progress class="m-4" value={progress} {max} />
                    {#if progressMessage}
                        <i class="text-center">
                            {progressMessage}
                        </i>
                    {/if}
                    <button
                        class="btn variant-filled mt-4"
                        disabled={!(progress === 0)}
                        on:click={generateEmbeddings}
                    >
                        Generate embeddings
                    </button>
                </div>
            </Step>
        </Stepper>
    </div>
</div>
