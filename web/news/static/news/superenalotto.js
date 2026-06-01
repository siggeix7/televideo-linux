(function () {
    "use strict";

    const body = document.body;
    const apiUrl = body.dataset.apiUrl;
    const refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
    const yearButtons = document.getElementById("year-buttons");
    const drawsTbody = document.getElementById("draws-tbody");
    const drawCount = document.getElementById("draw-count");
    const drawDetail = document.getElementById("draw-detail");
    const heading = document.getElementById("draw-heading");
    const drawDateText = document.getElementById("draw-date-text");
    const winningNumbers = document.getElementById("winning-numbers");
    const jollyNumber = document.getElementById("jolly-number");
    const superstarNumber = document.getElementById("superstar-number");
    const jackpot = document.getElementById("jackpot");
    const prizePool = document.getElementById("prize-pool");
    const emptyState = document.getElementById("empty-state");
    const errorState = document.getElementById("error-state");
    const errorMessage = document.getElementById("error-message");

    let language = "it";
    let selectedYear = localStorage.getItem("superenalotto-year") || "";
    let selectedDate = "";
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

    function numberChip(value) {
        var chip = document.createElement("span");
        chip.className = "number-chip";
        chip.textContent = value;
        return chip;
    }

    function numberChipSmall(value) {
        var chip = document.createElement("span");
        chip.className = "number-chip number-chip--small";
        chip.textContent = value;
        return chip;
    }

    function renderYearButtons(years) {
        yearButtons.replaceChildren();
        years.forEach(function (year) {
            var btn = document.createElement("button");
            btn.className = "year-btn" + (year === Number(selectedYear) ? " year-btn--active" : "");
            btn.textContent = year;
            btn.type = "button";
            btn.addEventListener("click", function () {
                if (Number(selectedYear) === year) return;
                selectedYear = String(year);
                selectedDate = "";
                localStorage.setItem("superenalotto-year", selectedYear);
                retryCount = 0;
                loadData();
            });
            yearButtons.appendChild(btn);
        });
    }

    function renderDrawsTable(draws) {
        drawsTbody.replaceChildren();

        if (!draws || draws.length === 0) {
            if (emptyState) emptyState.hidden = false;
            drawCount.textContent = "";
            return;
        }

        if (emptyState) emptyState.hidden = true;
        drawCount.textContent = draws.length + " " + (ui.draws_count || "estrazioni");

        draws.forEach(function (draw) {
            var tr = document.createElement("tr");
            tr.className = "draws-table__row";
            tr.tabIndex = 0;
            tr.setAttribute("role", "button");
            tr.setAttribute("aria-expanded", draw.draw_date === selectedDate ? "true" : "false");

            if (draw.draw_date === selectedDate) {
                tr.classList.add("draws-table__row--selected");
            }

            tr.addEventListener("click", function () {
                selectedDate = draw.draw_date;
                retryCount = 0;
                loadData();
            });
            tr.addEventListener("keydown", function (e) {
                if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    selectedDate = draw.draw_date;
                    retryCount = 0;
                    loadData();
                }
            });

            var tdNum = document.createElement("td");
            tdNum.textContent = draw.draw_number;
            tdNum.className = "draws-table__num";

            var tdDate = document.createElement("td");
            tdDate.textContent = draw.draw_date;
            tdDate.className = "draws-table__date";

            var tdNums = document.createElement("td");
            tdNums.className = "draws-table__numbers";
            draw.winning_numbers.forEach(function (n) {
                tdNums.appendChild(numberChipSmall(n));
            });

            var tdJolly = document.createElement("td");
            tdJolly.textContent = draw.jolly_number || "\u2014";
            tdJolly.className = "draws-table__jolly";

            var tdSs = document.createElement("td");
            tdSs.textContent = draw.superstar_number || "\u2014";
            tdSs.className = "draws-table__superstar";

            tr.appendChild(tdNum);
            tr.appendChild(tdDate);
            tr.appendChild(tdNums);
            tr.appendChild(tdJolly);
            tr.appendChild(tdSs);
            drawsTbody.appendChild(tr);
        });
    }

    function renderDraw(draw) {
        if (!draw) {
            if (drawDetail) drawDetail.hidden = true;
            heading.textContent = "";
            drawDateText.textContent = "";
            winningNumbers.replaceChildren();
            jollyNumber.textContent = "\u2014";
            superstarNumber.textContent = "\u2014";
            jackpot.textContent = "\u2014";
            prizePool.textContent = "\u2014";
            return;
        }
        if (drawDetail) drawDetail.hidden = false;
        heading.textContent = (ui.draw_label || "Concorso") + " N." + draw.draw_number;
        drawDateText.textContent = (ui.draw_date_label || "Data") + ": " + draw.draw_date;
        winningNumbers.replaceChildren.apply(winningNumbers, draw.winning_numbers.map(numberChip));
        jollyNumber.textContent = draw.jolly_number || "\u2014";
        superstarNumber.textContent = draw.superstar_number || "\u2014";
        jackpot.textContent = draw.jackpot.text || "\u2014";
        prizePool.textContent = draw.prize_pool.text || "\u2014";

        var detailTop = drawDetail.getBoundingClientRect().top + window.scrollY - 24;
        drawDetail.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    async function loadData() {
        var seq = ++requestSeq;
        if (activeController) activeController.abort();
        var controller = new AbortController();
        activeController = controller;
        loading = true;
        hideError();

        var url = new URL(apiUrl, window.location.origin);
        url.searchParams.set("lang", "it");
        if (selectedYear) {
            url.searchParams.set("year", selectedYear);
        }
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

            if (!selectedYear && payload.selected_year) {
                selectedYear = String(payload.selected_year);
                localStorage.setItem("superenalotto-year", selectedYear);
            }

            renderYearButtons(payload.years || []);
            renderDrawsTable(payload.draws || []);
            renderDraw(payload.selected);
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
                setTimeout(loadData, 2000 * retryCount);
            }
        } finally {
            clearTimeout(timeoutId);
            if (seq === requestSeq) activeController = null;
        }
    }

    loadData();
    setInterval(function () {
        if (!loading) loadData();
    }, refreshSeconds * 1000);
})();
