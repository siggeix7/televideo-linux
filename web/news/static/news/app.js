(function () {
    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Number(body.dataset.refreshSeconds || 60);
    const grid = document.getElementById("news-grid");
    const template = document.getElementById("news-card-template");
    const statusText = document.getElementById("status-text");
    const lastRefresh = document.getElementById("last-refresh");
    const emptyState = document.getElementById("empty-state");
    const buttons = Array.from(document.querySelectorAll("[data-language]"));
    const seen = new Set();
    let language = localStorage.getItem("chronica-language") || body.dataset.initialLanguage || "la";
    let firstRender = true;

    function setActiveLanguage() {
        buttons.forEach((button) => {
            button.classList.toggle("is-active", button.dataset.language === language);
        });
    }

    function formatDate(value) {
        if (!value) {
            return "data non disponibile";
        }
        const parsed = new Date(value);
        if (Number.isNaN(parsed.getTime())) {
            return value;
        }
        return parsed.toLocaleString("it-IT", { dateStyle: "medium", timeStyle: "short" });
    }

    function renderNews(payload) {
        grid.replaceChildren();
        emptyState.hidden = payload.items.length > 0;
        statusText.textContent = payload.error || `Cronaca aggiornata in ${payload.language_label}`;
        lastRefresh.textContent = formatDate(payload.generated_at);

        payload.items.forEach((item) => {
            const node = template.content.firstElementChild.cloneNode(true);
            node.querySelector("h2").textContent = item.title;
            node.querySelector(".news-card__meta").textContent = item.published || "Ultim'Ora Rai Televideo";
            node.querySelector(".news-card__source").textContent = `Fonte originale: ${item.source_title}`;
            node.querySelector(".news-card__summary").textContent = item.summary;
            const link = node.querySelector(".news-card__link");
            if (item.link) {
                link.href = item.link;
            } else {
                link.hidden = true;
            }
            if (!firstRender && !seen.has(item.id)) {
                node.classList.add("is-new");
            }
            seen.add(item.id);
            grid.appendChild(node);
        });
        firstRender = false;
    }

    async function loadNews() {
        const url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", language);
        try {
            const response = await fetch(url, { headers: { Accept: "application/json" } });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            renderNews(await response.json());
        } catch (error) {
            statusText.textContent = `Errore durante l'aggiornamento: ${error.message}`;
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

    setActiveLanguage();
    loadNews();
    setInterval(loadNews, Math.max(refreshSeconds, 15) * 1000);
})();
