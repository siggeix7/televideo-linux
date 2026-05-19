(function () {
    "use strict";

    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
    const grid = document.getElementById("news-grid");
    const template = document.getElementById("news-card-template");
    const skeletonTemplate = document.getElementById("skeleton-card-template");
    const statusText = document.getElementById("status-text");
    const lastRefresh = document.getElementById("last-refresh");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");
    const errorMessage = document.getElementById("error-message");
    const categoryList = document.getElementById("category-list");
    const previousPage = document.getElementById("previous-page");
    const nextPage = document.getElementById("next-page");
    const pageStatus = document.getElementById("page-status");
    const seen = new Set();
    const DEFAULT_LIMIT = 12;

    let language = body.dataset.initialLanguage || localStorage.getItem("chronica-language") || "la";
    if (body.dataset.initialLanguage) {
        localStorage.setItem("chronica-language", language);
    }
    let selectedCategory = localStorage.getItem("chronica-category") || "all";
    let page = Number(localStorage.getItem("chronica-page") || 1);
    let ui = {
        error_prefix: body.dataset.errorPrefix || "",
        timeout_error: body.dataset.timeoutError || "",
        unknown_error: body.dataset.unknownError || "",
        no_search_results_title: body.dataset.noSearchResultsTitle || "",
        no_search_results_message: body.dataset.noSearchResultsMessage || "",
    };
    let firstRender = true;
    let loading = false;
    let retryCount = 0;
    const MAX_RETRIES = 3;

    function applyUi(nextUi) {
        ui = nextUi || ui;
        if (ui.html_lang) {
            document.documentElement.lang = ui.html_lang;
        }
        document.querySelectorAll("[data-ui]").forEach(function (node) {
            var key = node.dataset.ui;
            if (ui[key]) {
                node.textContent = ui[key];
            }
        });
        document.querySelectorAll("[data-ui-placeholder]").forEach(function (node) {
            var key = node.dataset.uiPlaceholder;
            if (ui[key]) {
                node.setAttribute("placeholder", ui[key]);
                node.setAttribute("aria-label", ui[key]);
            }
        });
    }

    function formatDate(value) {
        if (!value) return ui.date_unavailable || "data non disponibile";
        var parsed = new Date(value);
        if (isNaN(parsed.getTime())) return value;
        return parsed.toLocaleString(language === "en" ? "en-GB" : "it-IT", {
            dateStyle: "medium",
            timeStyle: "short",
        });
    }

    function showSkeletons(count) {
        if (!skeletonTemplate) return;
        grid.replaceChildren();
        for (var i = 0; i < count; i++) {
            grid.appendChild(skeletonTemplate.content.firstElementChild.cloneNode(true));
        }
    }

    function hideError() {
        if (errorState) errorState.hidden = true;
    }

    function showError(msg) {
        if (errorState && errorMessage) {
            errorState.hidden = false;
            errorMessage.textContent = msg || ui.unknown_error || "Errore sconosciuto";
        }
        if (statusText) {
            statusText.textContent = (ui.error_prefix || "Errore:") + " " + (msg || "");
        }
    }

    function renderCategories(categories) {
        categoryList.replaceChildren();
        if (selectedCategory !== "all" && !categories.some(function (c) { return c.code === selectedCategory; })) {
            selectedCategory = "all";
            localStorage.setItem("chronica-category", selectedCategory);
        }

        var allCount = categories.reduce(function (sum, c) { return sum + Number(c.count || 0); }, 0);
        var allButton = document.createElement("button");
        allButton.type = "button";
        allButton.className = "category-button";
        allButton.dataset.category = "all";
        allButton.textContent = (ui.all_categories || "Tutte") + " (" + allCount + ")";
        categoryList.appendChild(allButton);

        categories.forEach(function (category) {
            var button = document.createElement("button");
            button.type = "button";
            button.className = "category-button";
            button.dataset.category = category.code;
            button.textContent = category.name + " (" + category.count + ")";
            categoryList.appendChild(button);
        });

        categoryList.querySelectorAll("[data-category]").forEach(function (button) {
            button.classList.toggle("is-active", button.dataset.category === selectedCategory);
            button.addEventListener("click", function () {
                selectedCategory = button.dataset.category;
                localStorage.setItem("chronica-category", selectedCategory);
                page = 1;
                localStorage.setItem("chronica-page", String(page));
                firstRender = true;
                retryCount = 0;
                loadNews();
            });
        });
    }

    function renderPagination(pagination) {
        var data = pagination || { page: 1, pages: 1, has_previous: false, has_next: false };
        page = data.page;
        localStorage.setItem("chronica-page", String(page));
        previousPage.textContent = ui.previous_page || "Precedenti";
        nextPage.textContent = ui.next_page || "Successive";
        previousPage.disabled = !data.has_previous;
        nextPage.disabled = !data.has_next;
        pageStatus.textContent = (ui.page_status || "Pagina {page} di {pages}")
            .replace("{page}", data.page)
            .replace("{pages}", data.pages);
    }

    function renderNews(payload) {
        applyUi(payload.ui);
        renderCategories(payload.categories || []);

        grid.replaceChildren();
        emptyState.hidden = payload.items.length > 0;

        var statusPrefix = payload.error ? (ui.error_prefix || "Errore:") + " " : "";
        statusText.textContent = statusPrefix + payload.error || (ui.updated || "Cronaca aggiornata in {language}").replace("{language}", payload.language_label);
        lastRefresh.textContent = formatDate(payload.generated_at);

        if (payload.error) {
            showError(payload.error);
        } else {
            hideError();
            retryCount = 0;
        }

        payload.items.forEach(function (item) {
            var node = template.content.firstElementChild.cloneNode(true);
            node.querySelector(".news-card__ribbon").textContent = ui.card_ribbon || "Novella";
            node.querySelector("h2").textContent = item.title;
            node.querySelector(".news-card__meta").textContent = item.published || "Ultim'Ora Rai Televideo";
            node.querySelector(".news-card__category").textContent = item.category_name
                ? (ui.category_prefix || "Categoria:") + " " + item.category_name
                : "";
            node.querySelector(".news-card__source").textContent =
                item.source_title && item.source_title !== item.title
                    ? (ui.source_prefix || "Titolo originale:") + " " + item.source_title
                    : "";
            node.querySelector(".news-card__summary").textContent = item.summary;
            if (!firstRender && !seen.has(item.id)) {
                node.classList.add("is-new");
            }
            seen.add(item.id);
            grid.appendChild(node);
        });

        renderPagination(payload.pagination);
        firstRender = false;
        loading = false;
    }

    async function loadNews() {
        if (loading) return;
        loading = true;
        hideError();

        showSkeletons(DEFAULT_LIMIT);

        var url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", language);
        url.searchParams.set("category", selectedCategory);
        url.searchParams.set("page", String(page));

        try {
            var response = await fetch(url, {
                headers: { Accept: "application/json" },
                signal: AbortSignal.timeout(15000),
            });
            if (!response.ok) throw new Error("HTTP " + response.status);
            renderNews(await response.json());
        } catch (error) {
            loading = false;
            grid.replaceChildren();
            emptyState.hidden = true;
            if (error.name === "TimeoutError" || error.name === "AbortError") {
                showError(ui.timeout_error || "Timeout: il server non risponde. Nuovo tentativo in corso...");
            } else {
                showError(error.message);
            }

            if (retryCount < MAX_RETRIES) {
                retryCount++;
                setTimeout(loadNews, 2000 * retryCount);
            }
        }
    }

    previousPage.addEventListener("click", function () {
        if (page > 1) {
            page -= 1;
            loadNews();
        }
    });

    nextPage.addEventListener("click", function () {
        page += 1;
        loadNews();
    });

    var searchInput = document.getElementById("search-input");
    if (searchInput) {
        var searchTimeout;
        searchInput.addEventListener("input", function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                var query = searchInput.value.toLowerCase().trim();
                var cards = grid.querySelectorAll(".news-card:not(.skeleton)");
                var visible = 0;
                cards.forEach(function (card) {
                    var text = (card.textContent || "").toLowerCase();
                    var match = !query || text.indexOf(query) !== -1;
                    card.style.display = match ? "" : "none";
                    if (match) visible++;
                });
                if (query && visible === 0 && cards.length > 0) {
                    emptyState.hidden = false;
                    emptyState.querySelector("h2").textContent = ui.no_search_results_title || "Nessun risultato";
                    emptyState.querySelector("p").textContent = (ui.no_search_results_message || 'Nessuna notizia contiene "{query}".')
                        .replace("{query}", query);
                } else if (!query) {
                    emptyState.hidden = true;
                }
            }, 200);
        });
    }

    loadNews();
    setInterval(function () {
        if (!loading) loadNews();
    }, refreshSeconds * 1000);
})();
