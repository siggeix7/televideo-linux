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
    const dateInput = document.getElementById("date-input");
    const clearDate = document.getElementById("clear-date");
    const previousPage = document.getElementById("previous-page");
    const nextPage = document.getElementById("next-page");
    const pageStatus = document.getElementById("page-status");
    const limitOptions = Array.from(document.querySelectorAll(".pagination__limit-option"));
    const limitOptionValues = limitOptions.map(function (button) {
        return Number(button.dataset.limit);
    }).filter(Boolean);
    const searchInput = document.getElementById("search-input");
    const clearSearch = document.getElementById("clear-search");
    const seen = new Set();
    const DEFAULT_LIMIT = Math.max(Number(body.dataset.defaultLimit || body.dataset.initialLimit || 25), 1);
    const initialParams = new URLSearchParams(window.location.search);
    const hasServerRendered = grid && grid.dataset.serverRendered === "true";
    const reduceMotion = window.matchMedia ? window.matchMedia("(prefers-reduced-motion: reduce)") : null;

    let language = "it";
    let page = Math.max(Number(initialParams.get("page") || localStorage.getItem("chronica-page") || 1) || 1, 1);
    let limit = normalizeLimit(initialParams.get("limit") || localStorage.getItem("chronica-limit") || body.dataset.initialLimit || DEFAULT_LIMIT);
    let searchQuery = initialParams.get("q") || "";
    let selectedDate = initialParams.get("date") || "";
    let ui = {
        error_prefix: body.dataset.errorPrefix || "",
        timeout_error: body.dataset.timeoutError || "",
        unknown_error: body.dataset.unknownError || "",
        no_search_results_title: body.dataset.noSearchResultsTitle || "",
        no_search_results_message: body.dataset.noSearchResultsMessage || "",
        no_date_results_title: "",
        no_date_results_message: "",
    };
    let firstRender = true;
    let loading = false;
    let retryCount = 0;
    let activeController = null;
    let requestSeq = 0;
    let searchTimeout = null;
    const MAX_RETRIES = 3;

    function scrollToTop() {
        window.scrollTo({ top: 0, behavior: reduceMotion && reduceMotion.matches ? "auto" : "smooth" });
    }

    function setGridBusy(isBusy) {
        if (grid) {
            grid.setAttribute("aria-busy", isBusy ? "true" : "false");
        }
    }

    function appendHighlightedText(node, text, query) {
        var source = String(text || "");
        var needle = String(query || "").trim();
        node.replaceChildren();
        if (!needle) {
            node.textContent = source;
            return;
        }

        var lowerSource = source.toLocaleLowerCase("it-IT");
        var lowerNeedle = needle.toLocaleLowerCase("it-IT");
        var cursor = 0;
        var matchIndex = lowerSource.indexOf(lowerNeedle, cursor);
        if (matchIndex === -1) {
            node.textContent = source;
            return;
        }

        while (matchIndex !== -1) {
            if (matchIndex > cursor) {
                node.appendChild(document.createTextNode(source.slice(cursor, matchIndex)));
            }
            var mark = document.createElement("mark");
            mark.className = "search-hit";
            mark.textContent = source.slice(matchIndex, matchIndex + needle.length);
            node.appendChild(mark);
            cursor = matchIndex + needle.length;
            matchIndex = lowerSource.indexOf(lowerNeedle, cursor);
        }

        if (cursor < source.length) {
            node.appendChild(document.createTextNode(source.slice(cursor)));
        }
    }

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
        return parsed.toLocaleString("it-IT", {
            dateStyle: "medium",
            timeStyle: "short",
        });
    }

    function formatPublished(item) {
        if (item.published_iso) return formatDate(item.published_iso);
        return item.published || "Ultim'Ora Rai Televideo";
    }

    function updateSearchControls() {
        if (searchInput && searchInput.value !== searchQuery) {
            searchInput.value = searchQuery;
        }
        if (clearSearch) {
            clearSearch.hidden = !searchQuery;
        }
    }

    function updateDateControls(dateMin, dateMax) {
        if (!dateInput) return;
        if (dateInput.value !== selectedDate) {
            dateInput.value = selectedDate;
        }
        if (dateMin) dateInput.min = dateMin;
        else dateInput.removeAttribute("min");
        if (dateMax) dateInput.max = dateMax;
        else dateInput.removeAttribute("max");
        if (clearDate) {
            clearDate.hidden = !selectedDate;
            clearDate.textContent = ui.date_filter_all || "Tutti i giorni";
        }
    }

    function normalizeLimit(value) {
        var parsed = Number(value || DEFAULT_LIMIT);
        if (limitOptionValues.length && limitOptionValues.indexOf(parsed) === -1) {
            return DEFAULT_LIMIT;
        }
        return Math.max(parsed || DEFAULT_LIMIT, 1);
    }

    function updateLimitControls() {
        limitOptions.forEach(function (button) {
            var active = Number(button.dataset.limit) === limit;
            button.classList.toggle("is-active", active);
            button.setAttribute("aria-pressed", active ? "true" : "false");
        });
    }

    function updateAddressBar() {
        var params = new URLSearchParams();
        if (searchQuery) params.set("q", searchQuery);
        if (selectedDate) params.set("date", selectedDate);
        if (page > 1) params.set("page", String(page));
        if (limit !== DEFAULT_LIMIT) params.set("limit", String(limit));
        var nextUrl = window.location.pathname + (params.toString() ? "?" + params.toString() : "");
        if (nextUrl !== window.location.pathname + window.location.search) {
            window.history.replaceState(null, "", nextUrl);
        }
    }

    function showSkeletons(count) {
        if (!skeletonTemplate) return;
        setGridBusy(true);
        grid.classList.add("is-loading");
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
    }

    function renderPagination(pagination) {
        var data = pagination || { page: 1, pages: 1, has_previous: false, has_next: false };
        page = data.page;
        if (data.limit) {
            limit = normalizeLimit(data.limit);
            localStorage.setItem("chronica-limit", String(limit));
        }
        localStorage.setItem("chronica-page", String(page));
        updateLimitControls();
        previousPage.textContent = ui.previous_page || "Precedenti";
        nextPage.textContent = ui.next_page || "Successive";
        previousPage.disabled = !data.has_previous;
        nextPage.disabled = !data.has_next;
        pageStatus.textContent = (ui.page_status || "Pagina {page} di {pages}")
            .replace("{page}", data.page)
            .replace("{pages}", data.pages);
        updateAddressBar();
    }

    function renderNews(payload) {
        applyUi(payload.ui);
        if (Object.prototype.hasOwnProperty.call(payload, "search_query")) {
            searchQuery = payload.search_query || "";
        }
        if (Object.prototype.hasOwnProperty.call(payload, "selected_date")) {
            selectedDate = payload.selected_date || "";
        }
        updateSearchControls();
        updateDateControls(payload.date_min, payload.date_max);

        grid.classList.remove("is-loading");
        setGridBusy(false);
        grid.replaceChildren();

        var hasError = !!payload.error;
        hideError();
        emptyState.hidden = true;

        if (hasError) {
            showError(payload.error);
            statusText.textContent = (ui.error_prefix || "Errore:") + " " + payload.error;
            lastRefresh.textContent = formatDate(payload.generated_at);
            renderPagination(payload.pagination);
            return;
        }

        if (payload.items.length === 0) {
            emptyState.hidden = false;
            if (payload.search_query) {
                emptyState.querySelector("h2").textContent = ui.no_search_results_title || "Nessun risultato";
                emptyState.querySelector("p").textContent = (ui.no_search_results_message || 'Nessuna notizia contiene "{query}".')
                    .replace("{query}", payload.search_query);
            } else if (payload.selected_date) {
                emptyState.querySelector("h2").textContent = ui.no_date_results_title || "Nessuna notizia in questa data";
                emptyState.querySelector("p").textContent = ui.no_date_results_message || "";
            } else {
                emptyState.querySelector("h2").textContent = ui.empty_title || "Nessuna notizia";
                emptyState.querySelector("p").textContent = ui.empty_message || "";
            }
        }

        var total = payload.pagination && typeof payload.pagination.total === "number" ? payload.pagination.total : null;
        var totalSuffix = total === null ? "" : " · " + total + (total === 1 ? " notizia" : " notizie");
        statusText.textContent = (payload.search_query ? "Risultati aggiornati" : (ui.updated || "Notizie aggiornate")) + totalSuffix;
        lastRefresh.textContent = formatDate(payload.generated_at);
        retryCount = 0;

        var grouped = new Map();
        payload.items.forEach(function (item) {
            var key = item.published_date || "unknown";
            if (!grouped.has(key)) {
                grouped.set(key, {
                    name: item.published_date_label || ui.date_unavailable || "data non disponibile",
                    items: [],
                });
            }
            grouped.get(key).items.push(item);
        });

        grouped.forEach(function (group) {
            var section = document.createElement("section");
            section.className = "news-group animate-in";

            var header = document.createElement("div");
            header.className = "news-group__header";
            var title = document.createElement("h2");
            title.textContent = group.name;
            var count = document.createElement("span");
            count.textContent = String(group.items.length);
            header.appendChild(title);
            header.appendChild(count);
            section.appendChild(header);

            var cards = document.createElement("div");
            cards.className = "news-group__grid";

            group.items.forEach(function (item) {
                var node = template.content.firstElementChild.cloneNode(true);
                node.querySelector(".news-card__ribbon").textContent = ui.card_ribbon || "Novella";
                var heading = node.querySelector("h2");
                appendHighlightedText(heading, item.title, searchQuery);
                node.querySelector(".news-card__meta").textContent = formatPublished(item);
                node.querySelector(".news-card__source").textContent =
                    item.source_title && item.source_title !== item.title
                        ? (ui.source_prefix || "Titolo originale:") + " " + item.source_title
                        : "";
                appendHighlightedText(node.querySelector(".news-card__summary"), item.summary, searchQuery);
                if (!firstRender && !seen.has(item.id)) {
                    node.classList.add("is-new");
                }
                seen.add(item.id);
                cards.appendChild(node);
            });

            section.appendChild(cards);
            grid.appendChild(section);
            requestAnimationFrame(function () {
                section.classList.add("is-visible");
            });
        });

        renderPagination(payload.pagination);
        firstRender = false;
        loading = false;
    }

    async function loadNews(options) {
        options = options || {};
        var quiet = !!options.quiet;
        var seq = ++requestSeq;
        if (activeController) activeController.abort();
        var controller = new AbortController();
        activeController = controller;
        loading = true;
        setGridBusy(true);
        hideError();

        if (!quiet) showSkeletons(Math.min(limit, DEFAULT_LIMIT));
        if (searchQuery && statusText) {
            statusText.textContent = ui.searching_status || "Cerco nell'archivio...";
        }

        var url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", "it");
        url.searchParams.set("page", String(page));
        url.searchParams.set("limit", String(limit));
        if (selectedDate) {
            url.searchParams.set("date", selectedDate);
        }
        if (searchQuery) {
            url.searchParams.set("q", searchQuery);
        }
        var timeoutId = setTimeout(function () { controller.abort(); }, 15000);

        try {
            var response = await fetch(url, {
                headers: { Accept: "application/json" },
                signal: controller.signal,
            });
            if (!response.ok) throw new Error("HTTP " + response.status);
            var payload = await response.json();
            if (seq !== requestSeq) return;
            renderNews(payload);
        } catch (error) {
            if (seq !== requestSeq) return;
            loading = false;
            grid.classList.remove("is-loading");
            setGridBusy(false);
            grid.replaceChildren();
            emptyState.hidden = true;
            var errMsg;
            if (error.name === "TimeoutError" || error.name === "AbortError") {
                errMsg = ui.timeout_error || "Timeout";
                showError(errMsg);
            } else {
                errMsg = error.message;
                showError(errMsg);
            }
            statusText.textContent = (ui.error_prefix || "Errore:") + " " + errMsg;

            if (!searchQuery && retryCount < MAX_RETRIES) {
                retryCount++;
                setTimeout(function () { loadNews({ quiet: true }); }, 2000 * retryCount);
            }
        } finally {
            clearTimeout(timeoutId);
            if (seq === requestSeq) activeController = null;
        }
    }

    previousPage.addEventListener("click", function () {
        if (page > 1) {
            page -= 1;
            scrollToTop();
            loadNews();
        }
    });

    nextPage.addEventListener("click", function () {
        page += 1;
        scrollToTop();
        loadNews();
    });

    limitOptions.forEach(function (button) {
        button.addEventListener("click", function () {
            var nextLimit = normalizeLimit(button.dataset.limit);
            if (nextLimit === limit) return;
            limit = nextLimit;
            page = 1;
            localStorage.setItem("chronica-limit", String(limit));
            localStorage.setItem("chronica-page", String(page));
            firstRender = true;
            retryCount = 0;
            updateLimitControls();
            scrollToTop();
            loadNews();
        });
    });

    if (searchInput) {
        searchInput.addEventListener("input", function () {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(function () {
                var query = searchInput.value.trim();
                if (query === searchQuery) return;
                searchQuery = query;
                page = 1;
                localStorage.setItem("chronica-page", String(page));
                firstRender = true;
                retryCount = 0;
                loadNews();
            }, 200);
        });
    }

    if (clearSearch) {
        clearSearch.addEventListener("click", function () {
            if (!searchQuery && !searchInput.value) return;
            searchQuery = "";
            searchInput.value = "";
            page = 1;
            firstRender = true;
            retryCount = 0;
            updateSearchControls();
            loadNews();
            searchInput.focus();
        });
    }

    if (dateInput) {
        dateInput.addEventListener("change", function () {
            selectedDate = dateInput.value || "";
            page = 1;
            localStorage.setItem("chronica-page", String(page));
            firstRender = true;
            retryCount = 0;
            loadNews();
        });
    }

    if (clearDate) {
        clearDate.addEventListener("click", function () {
            if (!selectedDate && !dateInput.value) return;
            selectedDate = "";
            dateInput.value = "";
            page = 1;
            localStorage.setItem("chronica-page", String(page));
            firstRender = true;
            retryCount = 0;
            updateDateControls();
            loadNews();
            dateInput.focus();
        });
    }

    updateSearchControls();
    updateDateControls();
    updateLimitControls();
    loadNews({ quiet: hasServerRendered });

    var priorItemCount = 0;
    var toastEl = document.getElementById("update-toast");
    var toastTimeout = null;

    function showToast(message) {
        if (!toastEl) return;
        toastEl.textContent = message;
        toastEl.hidden = false;
        clearTimeout(toastTimeout);
        toastTimeout = setTimeout(function () {
            toastEl.hidden = true;
        }, 4000);
    }

    var originalRenderNews = renderNews;
    renderNews = function (payload) {
        var newCount = (payload.items || []).length;
        var wasFirstRender = firstRender;
        originalRenderNews(payload);
        if (!wasFirstRender && !payload.error && newCount !== priorItemCount && !payload.search_query && !payload.selected_date) {
            showToast("Aggiornamento: " + newCount + " notizie caricate");
        }
        priorItemCount = newCount;
    };

    setInterval(function () {
        if (!loading) loadNews({ quiet: true });
    }, refreshSeconds * 1000);
})();
