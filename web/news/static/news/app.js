(function () {
    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Number(body.dataset.refreshSeconds || 60);
    const grid = document.getElementById("news-grid");
    const template = document.getElementById("news-card-template");
    const statusText = document.getElementById("status-text");
    const lastRefresh = document.getElementById("last-refresh");
    const emptyState = document.getElementById("empty-state");
    const categoryList = document.getElementById("category-list");
    const previousPage = document.getElementById("previous-page");
    const nextPage = document.getElementById("next-page");
    const pageStatus = document.getElementById("page-status");
    const buttons = Array.from(document.querySelectorAll("[data-language]"));
    const seen = new Set();
    let language = localStorage.getItem("chronica-language") || body.dataset.initialLanguage || "la";
    let selectedCategory = localStorage.getItem("chronica-category") || "all";
    let page = Number(localStorage.getItem("chronica-page") || 1);
    let ui = {};
    let firstRender = true;

    function setActiveLanguage() {
        buttons.forEach((button) => button.classList.toggle("is-active", button.dataset.language === language));
    }

    function applyUi(nextUi) {
        ui = nextUi || ui;
        if (ui.html_lang) {
            document.documentElement.lang = ui.html_lang;
        }
        document.querySelectorAll("[data-ui]").forEach((node) => {
            const key = node.dataset.ui;
            if (ui[key]) {
                node.textContent = ui[key];
            }
        });
    }

    function formatDate(value) {
        if (!value) {
            return ui.date_unavailable || "data non disponibile";
        }
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return value;
        }
        return parsed.toLocaleString(language === "en" ? "en-GB" : "it-IT", { dateStyle: "medium", timeStyle: "short" });
    }

    function renderCategories(categories) {
        categoryList.replaceChildren();
        if (selectedCategory !== "all" && !categories.some((category) => category.code === selectedCategory)) {
            selectedCategory = "all";
            localStorage.setItem("chronica-category", selectedCategory);
        }
        const allCount = categories.reduce((sum, category) => sum + Number(category.count || 0), 0);
        const allButton = document.createElement("button");
        allButton.type = "button";
        allButton.className = "category-button";
        allButton.dataset.category = "all";
        allButton.textContent = `${ui.all_categories || "Tutte"} (${allCount})`;
        categoryList.appendChild(allButton);

        categories.forEach((category) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "category-button";
            button.dataset.category = category.code;
            button.textContent = `${category.name} (${category.count})`;
            categoryList.appendChild(button);
        });

        categoryList.querySelectorAll("[data-category]").forEach((button) => {
            button.classList.toggle("is-active", button.dataset.category === selectedCategory);
            button.addEventListener("click", () => {
                selectedCategory = button.dataset.category;
                localStorage.setItem("chronica-category", selectedCategory);
                page = 1;
                localStorage.setItem("chronica-page", String(page));
                firstRender = true;
                loadNews();
            });
        });
    }

    function renderPagination(pagination) {
        const data = pagination || { page: 1, pages: 1, has_previous: false, has_next: false };
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
        selectedCategory = payload.selected_category || selectedCategory;
        grid.replaceChildren();
        emptyState.hidden = payload.items.length > 0;
        statusText.textContent = payload.error || (ui.updated || "Cronaca aggiornata in {language}").replace("{language}", payload.language_label);
        lastRefresh.textContent = formatDate(payload.generated_at);

        payload.items.forEach((item) => {
            const node = template.content.firstElementChild.cloneNode(true);
            node.querySelector(".news-card__ribbon").textContent = ui.card_ribbon || "Novella";
            node.querySelector("h2").textContent = item.title;
            node.querySelector(".news-card__meta").textContent = item.published || "Ultim'Ora Rai Televideo";
            node.querySelector(".news-card__category").textContent = item.category_name ? `${ui.category_prefix || "Categoria:"} ${item.category_name}` : "";
            node.querySelector(".news-card__source").textContent = item.source_title && item.source_title !== item.title
                ? `${ui.source_prefix || "Titolo originale:"} ${item.source_title}`
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
    }

    async function loadNews() {
        const url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", language);
        url.searchParams.set("category", selectedCategory);
        url.searchParams.set("page", String(page));
        try {
            const response = await fetch(url, { headers: { Accept: "application/json" } });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            renderNews(await response.json());
        } catch (error) {
            statusText.textContent = `${ui.error_prefix || "Errore durante l'aggiornamento:"} ${error.message}`;
        }
    }

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            language = button.dataset.language;
            localStorage.setItem("chronica-language", language);
            firstRender = true;
            setActiveLanguage();
            loadNews();
        });
    });

    previousPage.addEventListener("click", () => {
        page = Math.max(1, page - 1);
        loadNews();
    });

    nextPage.addEventListener("click", () => {
        page += 1;
        loadNews();
    });

    setActiveLanguage();
    loadNews();
    setInterval(loadNews, Math.max(refreshSeconds, 15) * 1000);
})();
