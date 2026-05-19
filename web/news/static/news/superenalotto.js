(function () {
    "use strict";

    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
    const buttons = Array.from(document.querySelectorAll("[data-language]"));
    const dateSelect = document.getElementById("draw-date");
    const heading = document.getElementById("draw-heading");
    const drawDateText = document.getElementById("draw-date-text");
    const winningNumbers = document.getElementById("winning-numbers");
    const jollyNumber = document.getElementById("jolly-number");
    const superstarNumber = document.getElementById("superstar-number");
    const jackpot = document.getElementById("jackpot");
    const prizePool = document.getElementById("prize-pool");
    const chart = document.getElementById("trend-chart");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");
    const errorMessage = document.getElementById("error-message");

    let language = body.dataset.initialLanguage || localStorage.getItem("chronica-language") || "la";
    if (body.dataset.initialLanguage) {
        localStorage.setItem("chronica-language", language);
    }
    let selectedDate = localStorage.getItem("superenalotto-date") || "";
    let ui = {};
    let loading = false;
    let retryCount = 0;
    const MAX_RETRIES = 3;

    function setActiveLanguage() {
        buttons.forEach(function (button) {
            button.classList.toggle("is-active", button.dataset.language === language);
        });
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
    }

    function hideError() {
        if (errorState) errorState.hidden = true;
    }

    function showError(msg) {
        if (errorState && errorMessage) {
            errorState.hidden = false;
            errorMessage.textContent = msg || "Errore sconosciuto";
        }
    }

    function renderDates(dates) {
        dateSelect.replaceChildren();
        dates.forEach(function (date) {
            var option = document.createElement("option");
            option.value = date.value;
            option.textContent = date.label;
            option.selected = date.value === selectedDate;
            dateSelect.appendChild(option);
        });
        if (!selectedDate && dates[0]) {
            selectedDate = dates[0].value;
            dateSelect.value = selectedDate;
        }
    }

    function numberChip(value) {
        var chip = document.createElement("span");
        chip.className = "number-chip";
        chip.textContent = value;
        return chip;
    }

    function renderDraw(draw) {
        if (emptyState) emptyState.hidden = Boolean(draw);
        if (!draw) {
            heading.textContent = "";
            drawDateText.textContent = "";
            winningNumbers.replaceChildren();
            jollyNumber.textContent = "\u2014";
            superstarNumber.textContent = "\u2014";
            jackpot.textContent = "\u2014";
            prizePool.textContent = "\u2014";
            return;
        }
        heading.textContent = (ui.draw_label || "Concorso") + " N." + draw.draw_number;
        drawDateText.textContent = (ui.draw_date_label || "Data") + ": " + draw.draw_date;
        winningNumbers.replaceChildren.apply(winningNumbers, draw.winning_numbers.map(numberChip));
        jollyNumber.textContent = draw.jolly_number || "\u2014";
        superstarNumber.textContent = draw.superstar_number || "\u2014";
        jackpot.textContent = draw.jackpot.text || "\u2014";
        prizePool.textContent = draw.prize_pool.text || "\u2014";
    }

    function renderTrend(trend) {
        chart.replaceChildren();
        var maxValue = Math.max.apply(null, [1].concat(trend.map(function (point) {
            return Math.max(point.jackpot || 0, point.prize_pool || 0);
        })));

        trend.forEach(function (point) {
            var row = document.createElement("div");
            row.className = "trend-row";

            var label = document.createElement("span");
            label.textContent = point.label;

            var bars = document.createElement("div");
            bars.className = "trend-bars";

            var jackpotBar = document.createElement("i");
            jackpotBar.className = "trend-bar trend-bar--jackpot";
            jackpotBar.style.width = Math.max(2, ((point.jackpot || 0) / maxValue) * 100) + "%";

            var poolBar = document.createElement("i");
            poolBar.className = "trend-bar trend-bar--pool";
            poolBar.style.width = Math.max(2, ((point.prize_pool || 0) / maxValue) * 100) + "%";

            bars.appendChild(jackpotBar);
            bars.appendChild(poolBar);
            row.appendChild(label);
            row.appendChild(bars);
            chart.appendChild(row);
        });
    }

    async function loadDraw() {
        if (loading) return;
        loading = true;
        hideError();

        var url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", language);
        if (selectedDate) {
            url.searchParams.set("date", selectedDate);
        }

        try {
            var response = await fetch(url, {
                headers: { Accept: "application/json" },
                signal: AbortSignal.timeout(15000),
            });
            if (!response.ok) throw new Error("HTTP " + response.status);
            var payload = await response.json();
            applyUi(payload.ui);
            renderDates(payload.dates || []);
            renderDraw(payload.selected);
            renderTrend(payload.trend || []);
            retryCount = 0;
            loading = false;
        } catch (error) {
            loading = false;
            if (error.name === "TimeoutError" || error.name === "AbortError") {
                showError("Timeout: il server non risponde. Nuovo tentativo in corso...");
            } else {
                showError(error.message);
            }
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                setTimeout(loadDraw, 2000 * retryCount);
            }
        }
    }

    buttons.forEach(function (button) {
        button.addEventListener("click", function () {
            language = button.dataset.language;
            localStorage.setItem("chronica-language", language);
            retryCount = 0;
            setActiveLanguage();
            loadDraw();
        });
    });

    dateSelect.addEventListener("change", function () {
        selectedDate = dateSelect.value;
        localStorage.setItem("superenalotto-date", selectedDate);
        retryCount = 0;
        loadDraw();
    });

    setActiveLanguage();
    loadDraw();
    setInterval(function () {
        if (!loading) loadDraw();
    }, refreshSeconds * 1000);
})();
