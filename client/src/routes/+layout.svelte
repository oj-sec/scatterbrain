<script>
    import "../app.postcss";
    import { AppShell, AppBar } from "@skeletonlabs/skeleton";

    // Highlight JS
    import hljs from "highlight.js/lib/core";
    import "highlight.js/styles/github-dark.css";
    import { storeHighlightJs } from "@skeletonlabs/skeleton";
    import xml from "highlight.js/lib/languages/xml"; // for HTML
    import css from "highlight.js/lib/languages/css";
    import javascript from "highlight.js/lib/languages/javascript";
    import typescript from "highlight.js/lib/languages/typescript";

    hljs.registerLanguage("xml", xml); // for HTML
    hljs.registerLanguage("css", css);
    hljs.registerLanguage("javascript", javascript);
    hljs.registerLanguage("typescript", typescript);
    storeHighlightJs.set(hljs);

    // Floating UI for Popups
    import {
        computePosition,
        autoUpdate,
        flip,
        shift,
        offset,
        arrow,
    } from "@floating-ui/dom";
    import { storePopup } from "@skeletonlabs/skeleton";
    storePopup.set({ computePosition, autoUpdate, flip, shift, offset, arrow });

    // Font Awesome
    import "@fortawesome/fontawesome-free/css/fontawesome.css";
    import "@fortawesome/fontawesome-free/css/brands.css";
    import "@fortawesome/fontawesome-free/css/solid.css";
    import "@fortawesome/fontawesome-free/css/regular.css";

    // Toasts
    import { initializeStores, Toast } from "@skeletonlabs/skeleton";
    initializeStores();
</script>

<!-- App Shell -->
<Toast />
<AppShell>
    <svelte:fragment slot="header">
        <!-- App Bar -->
        <AppBar>
            <svelte:fragment slot="lead">
                <a href="/"
                    ><strong class="text-xl uppercase">Scatterbrain</strong></a
                >
            </svelte:fragment>
            <svelte:fragment slot="trail">
                <a
                    class="btn btn-sm variant-ghost-surface"
                    href="https://github.com/oj-sec/scatterbrain"
                    target="_blank"
                    rel="noreferrer"
                >
                    GitHub
                </a>
            </svelte:fragment>
        </AppBar>
    </svelte:fragment>
    <!-- Page Route Content -->
    <slot />
</AppShell>
