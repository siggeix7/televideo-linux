(function () {
    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Number(body.dataset.refreshSeconds || 60);
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
    let language = body.dataset.initialLanguage || localStorage.getItem("chronica-language") || "la";
    if (body.dataset.initialLanguage) {
        localStorage.setItem("chronica-language", language);
    }
    let selectedDate = localStorage.getItem("superenalotto-date") || "";
    let ui = {};

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

    function renderDates(dates) {
        dateSelect.replaceChildren();
        dates.forEach((date) => {
            const option = document.createElement("option");
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
        const chip = document.createElement("span");
        chip.className = "number-chip";
        chip.textContent = value;
        return chip;
    }

    function renderDraw(draw) {
        emptyState.hidden = Boolean(draw);
        if (!draw) {
            heading.textContent = "";
            drawDateText.textContent = "";
            winningNumbers.replaceChildren();
            jollyNumber.textContent = "-";
            superstarNumber.textContent = "-";
            jackpot.textContent = "-";
            prizePool.textContent = "-";
            return;
        }
        heading.textContent = `${ui.draw_label || "Concorso"} N.${draw.draw_number}`;
        drawDateText.textContent = `${ui.draw_date_label || "Data"}: ${draw.draw_date}`;
        winningNumbers.replaceChildren(...draw.winning_numbers.map(numberChip));
        jollyNumber.textContent = draw.jolly_number || "-";
        superstarNumber.textContent = draw.superstar_number || "-";
        jackpot.textContent = draw.jackpot.text || "-";
        prizePool.textContent = draw.prize_pool.text || "-";
    }

    function renderTrend(trend) {
        chart.replaceChildren();
        const maxValue = Math.max(1, ...trend.map((point) => Math.max(point.jackpot || 0, point.prize_pool || 0)));
        trend.forEach((point) => {
            const row = document.createElement("div");
            row.className = "trend-row";
            const label = document.createElement("span");
            label.textContent = point.label;
            const bars = document.createElement("div");
            bars.className = "trend-bars";
            const jackpotBar = document.createElement("i");
            jackpotBar.className = "trend-bar trend-bar--jackpot";
            jackpotBar.style.width = `${Math.max(2, ((point.jackpot || 0) / maxValue) * 100)}%`;
            const poolBar = document.createElement("i");
            poolBar.className = "trend-bar trend-bar--pool";
            poolBar.style.width = `${Math.max(2, ((point.prize_pool || 0) / maxValue) * 100)}%`;
            bars.append(jackpotBar, poolBar);
            row.append(label, bars);
            chart.appendChild(row);
        });
    }

    async function loadDraw() {
        const url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", language);
        if (selectedDate) {
            url.searchParams.set("date", selectedDate);
        }
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        const payload = await response.json();
        applyUi(payload.ui);
        renderDates(payload.dates || []);
        renderDraw(payload.selected);
        renderTrend(payload.trend || []);
    }

    buttons.forEach((button) => {
        button.addEventListener("click", () => {
            language = button.dataset.language;
            localStorage.setItem("chronica-language", language);
            setActiveLanguage();
            loadDraw();
        });
    });

    dateSelect.addEventListener("change", () => {
        selectedDate = dateSelect.value;
        localStorage.setItem("superenalotto-date", selectedDate);
        loadDraw();
    });

    setActiveLanguage();
    loadDraw();
    setInterval(loadDraw, Math.max(refreshSeconds, 15) * 1000);
})();
