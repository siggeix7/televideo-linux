(function () {
    "use strict";

    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
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

    let language = "it";
    let selectedDate = localStorage.getItem("superenalotto-date") || "";
    let ui = {
        timeout_error: body.dataset.timeoutError || "",
        unknown_error: body.dataset.unknownError || "",
    };
    let loading = false;
    let retryCount = 0;
    let activeController = null;
    let requestSeq = 0;
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

    function renderDates(dates, nextSelectedDate) {
        if (nextSelectedDate) {
            selectedDate = nextSelectedDate;
        }
        if (selectedDate && !dates.some(function (date) { return date.value === selectedDate; })) {
            selectedDate = dates[0] ? dates[0].value : "";
        }
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
        }
        if (selectedDate) {
            dateSelect.value = selectedDate;
            localStorage.setItem("superenalotto-date", selectedDate);
        } else {
            localStorage.removeItem("superenalotto-date");
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
        var seq = ++requestSeq;
        if (activeController) activeController.abort();
        var controller = new AbortController();
        activeController = controller;
        loading = true;
        hideError();

        var url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", "it");
        if (selectedDate) {
            url.searchParams.set("date", selectedDate);
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
            applyUi(payload.ui);
            renderDates(payload.dates || [], payload.selected_date || (payload.selected && payload.selected.draw_date) || "");
            renderDraw(payload.selected);
            renderTrend(payload.trend || []);
            retryCount = 0;
            loading = false;
        } catch (error) {
            if (seq !== requestSeq) return;
            loading = false;
            if (error.name === "TimeoutError" || error.name === "AbortError") {
                showError(ui.timeout_error || "Timeout: il server non risponde. Nuovo tentativo in corso...");
            } else {
                showError(error.message);
            }
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                setTimeout(loadDraw, 2000 * retryCount);
            }
        } finally {
            clearTimeout(timeoutId);
            if (seq === requestSeq) activeController = null;
        }
    }

    dateSelect.addEventListener("change", function () {
        selectedDate = dateSelect.value;
        localStorage.setItem("superenalotto-date", selectedDate);
        retryCount = 0;
        loadDraw();
    });

    loadDraw();
    setInterval(function () {
        if (!loading) loadDraw();
    }, refreshSeconds * 1000);
})();
