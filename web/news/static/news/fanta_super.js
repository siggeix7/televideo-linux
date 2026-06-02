(function () {
    "use strict";

    var body = document.body;
    var apiUrl = body.dataset.apiUrl;
    var refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
    var section = document.getElementById("prediction-section");
    var loading = document.getElementById("prediction-loading");
    var emptyEl = document.getElementById("prediction-empty");
    var errorEl = document.getElementById("prediction-error");
    var errorMsg = document.getElementById("prediction-error-msg");
    var inFlight = false;

    var STRATEGY_ICONS = {
        "Ciclo di ritorno": "\u25C9",
        "Transizioni Markov": "\u25C8",
        "Gap anomalo": "\u25D6",
        "Tendenza recente": "\u25B3",
        "Mix controllato": "\u25A3",
        "Ensemble pesato": "\u2605",
    };

    var STRATEGY_COLORS = {
        "Ciclo di ritorno": "card--cycle",
        "Ensemble pesato": "card--ensemble",
    };

    function esc(s) {
        var d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    }

    function chip(n, extraClass) {
        return '<span class="number-chip' + (extraClass ? " " + extraClass : "") + '">' + n + '</span>';
    }

    function chipSmall(n, extraClass) {
        return '<span class="number-chip number-chip--small' + (extraClass ? " " + extraClass : "") + '">' + n + '</span>';
    }

    function renderCombo(combo, idx) {
        var label = combo.label || ("Combinazione " + (idx + 1));
        var icon = STRATEGY_ICONS[label] || "";
        var colorClass = STRATEGY_COLORS[label] || "";

        var h = "";
        h += '<article class="prediction-card ' + colorClass + '">';

        // Header
        h += '<div class="prediction-card__head">';
        if (icon) h += '<span class="prediction-card__icon" aria-hidden="true">' + icon + '</span>';
        h += '<div>';
        h += '<h2 class="prediction-card__title">' + esc(label) + '</h2>';
        h += '<p class="prediction-card__sub">' + esc(combo.description || "") + '</p>';
        h += '</div>';
        h += '</div>';

        // Numbers
        h += '<div class="prediction-card__numbers">';
        (combo.numbers || []).forEach(function (n) {
            h += chip(n);
        });
        h += '</div>';

        // Jolly + SuperStar
        h += '<div class="prediction-card__extras">';
        h += '<span><span class="prediction-card__extras-label">Jolly</span> ' + chipSmall(combo.jolly || "-") + '</span>';
        h += '<span><span class="prediction-card__extras-label">SuperStar</span> ' + chipSmall(combo.superstar || "-", "number-chip--special") + '</span>';
        h += '</div>';

        // Reasoning
        if (combo.reasoning && combo.reasoning.length) {
            h += '<details class="prediction-card__details">';
            h += '<summary>Come viene calcolata</summary>';
            h += '<ul>';
            combo.reasoning.forEach(function (r) {
                h += '<li>' + esc(r) + '</li>';
            });
            h += '</ul>';
            if (combo.cycle_details && combo.cycle_details.length) {
                h += '<p class="prediction-card__details-sub">Gap attuali:</p>';
                h += '<ul>';
                combo.cycle_details.forEach(function (d) {
                    h += '<li>' + esc(d) + '</li>';
                });
                h += '</ul>';
            }
            if (combo.gap_details && combo.gap_details.length) {
                h += '<p class="prediction-card__details-sub">Dettaglio gap:</p>';
                h += '<ul>';
                combo.gap_details.forEach(function (d) {
                    h += '<li>' + esc(d) + '</li>';
                });
                h += '</ul>';
            }
            if (combo.context) {
                h += '<p class="prediction-card__context">' + esc(combo.context) + '</p>';
            }
            h += '</details>';
        }

        h += '</article>';
        return h;
    }

    function renderAnalysis(analysis) {
        if (!analysis || !analysis.total_draws) return "";

        var h = "";

        // --- Stats bar ---
        h += '<div class="analysis-bar">';
        h += '<span>' + analysis.total_draws + ' estrazioni analizzate</span>';
        h += '<span>Baseline casuale: ' + analysis.random_baseline + ' match/estr.</span>';
        if (analysis.last_draw) {
            h += '<span>Ultima: ' + esc(analysis.last_draw.date);
            (analysis.last_draw.numbers || []).forEach(function (n) {
                h += " " + chipSmall(n);
            });
            h += '</span>';
        }
        h += '</div>';

        // --- Methodology performance comparison ---
        if (analysis.methodology) {
            h += '<details class="analysis-block analysis-block--methodology">';
            h += '<summary>Performance delle strategie nei backtest</summary>';
            h += '<table class="analysis-table">';
            h += '<thead><tr><th>Strategia</th><th>Match medi/estrazione</th><th>Note</th></tr></thead>';
            h += '<tbody>';
            var methods = analysis.methodology;
            Object.keys(methods).forEach(function (key) {
                var m = methods[key];
                var nameMap = {
                    cycle_aware: "Ciclo di ritorno",
                    markov: "Transizioni Markov",
                    overdue: "Gap anomalo",
                    hot: "Tendenza recente",
                };
                var name = nameMap[key] || key;
                var note = "";
                if (key === "cycle_aware") note = "p&lt;0.05 (significativo)";
                else note = "non significativo";
                h += '<tr>';
                h += '<td><strong>' + esc(name) + '</strong></td>';
                h += '<td>' + esc(m.avg_performance) + '</td>';
                h += '<td>' + note + '</td>';
                h += '</tr>';
            });
            h += '</tbody></table>';
            h += '</details>';
        }

        // --- Most overdue table ---
        if (analysis.most_overdue && analysis.most_overdue.length) {
            h += '<details class="analysis-block analysis-block--overdue" open>';
            h += '<summary>Numeri pi\u00f9 in ritardo</summary>';
            h += '<table class="analysis-table">';
            h += '<thead><tr><th>N.</th><th>Gap</th><th>Ciclo medio</th><th>Rapporto</th></tr></thead>';
            h += '<tbody>';
            analysis.most_overdue.forEach(function (item) {
                var n = item[0], gap = item[1], avg = item[2], ratio = item[3];
                var rowClass = ratio > 3 ? " analysis-row--hot" : "";
                h += '<tr class="' + rowClass + '">';
                h += '<td><strong>' + n + '</strong></td>';
                h += '<td>' + gap + ' estr.</td>';
                h += '<td>' + (avg || "-") + '</td>';
                h += '<td>' + ratio + 'x</td>';
                h += '</tr>';
            });
            h += '</tbody></table>';
            h += '</details>';
        }

        // --- Trending up ---
        if (analysis.trending_up && analysis.trending_up.length) {
            h += '<details class="analysis-block analysis-block--trends">';
            h += '<summary>Numeri in tendenza crescente</summary>';
            h += '<p class="analysis-note">Frequenza recente (ultime 100 estr.) superiore alla media storica.</p>';
            h += '<p class="analysis-trends">';
            analysis.trending_up.forEach(function (item) {
                h += chipSmall(item[0], "number-chip--trend");
            });
            h += '</p>';
            h += '</details>';
        }

        return '<section class="analysis-section">' + h + '</section>';
    }

    function renderHistory(history) {
        if (!history || !history.length) return "";

        var h = '<section class="history-section">';
        h += '<h2 class="history-section__title">Storico pronostici verificati</h2>';
        h += '<div class="history-list">';

        history.forEach(function (pred) {
            h += '<article class="history-item">';
            h += '<div class="history-item__head">';
            h += '<strong>Concorso N.' + pred.draw_number + ' del ' + esc(pred.target_draw_date) + '</strong>';
            h += '<span class="history-item__date">Pronostico del ' + (pred.created_at || "").slice(0, 10) + '</span>';
            h += '</div>';

            var totalHits = 0;
            (pred.matched_counts || []).forEach(function (mc) { totalHits += mc.matches; });

            h += '<div class="history-item__combos">';
            (pred.combinations || []).forEach(function (combo, idx) {
                var mc = pred.matched_counts && pred.matched_counts[idx];
                var m = mc ? mc.matches : 0;
                var jm = mc && mc.jolly_match;
                var sm = mc && mc.superstar_match;

                h += '<div class="history-combo' + (m > 0 ? ' has-match' : '') + '">';
                h += '<span class="history-combo__label">' + esc(combo.label || ("C" + (idx + 1))) + '</span>';
                h += '<span class="history-combo__nums">';
                (combo.numbers || []).forEach(function (n) {
                    h += chipSmall(n, m > 0 ? "number-chip--hit" : "number-chip--miss");
                });
                h += '</span>';
                h += '<span class="history-combo__result">';
                h += m + "/6";
                if (jm) h += " +J";
                if (sm) h += " +SS";
                h += '</span>';
                h += '</div>';
            });
            h += '</div>';

            h += '<div class="history-item__total">Totale match: ' + totalHits + '/36</div>';
            h += '</article>';
        });

        h += '</div></section>';
        return h;
    }

    function renderPage(prediction, analysis, history) {
        if (!prediction || !prediction.combinations || !prediction.combinations.length) {
            emptyEl.hidden = false;
            loading.hidden = true;
            section.setAttribute("aria-busy", "false");
            return;
        }

        loading.hidden = true;
        emptyEl.hidden = true;
        errorEl.hidden = true;

        var h = "";

        // --- Prediction header ---
        h += '<div class="prediction-header">';
        h += '<h2 class="prediction-header__title">Pronostico attuale</h2>';
        if (prediction.target_draw_date) {
            h += '<p class="prediction-header__target">Concorso N.' + prediction.draw_number + ' del <strong>' + esc(prediction.target_draw_date) + '</strong></p>';
        }
        if (prediction.created_at) {
            h += '<p class="prediction-header__generated">Generato: ' + esc(prediction.created_at.slice(0, 16).replace("T", " ")) + '</p>';
        }
        h += '</div>';

        // --- Combos grid ---
        h += '<div class="prediction-grid">';
        prediction.combinations.forEach(function (combo, idx) {
            h += renderCombo(combo, idx);
        });
        h += '</div>';

        // --- Analysis ---
        h += renderAnalysis(analysis);

        // --- Footer note ---
        h += '<p class="prediction-disclaimer">Il SuperEnalotto &egrave; un gioco casuale. La baseline teorica &egrave; 0.40 match a estrazione (6/90). Solo il Ciclo di ritorno ha mostrato significativit&agrave; statistica (p&lt;0.05). Nessuna strategia garantisce vincite.</p>';

        // --- History ---
        h += renderHistory(history);

        section.innerHTML = h;
        section.setAttribute("aria-busy", "false");
        section.classList.remove("is-visible");
        requestAnimationFrame(function () {
            section.classList.add("is-visible");
        });
    }

    function loadData() {
        if (inFlight) return;
        inFlight = true;
        section.setAttribute("aria-busy", "true");
        loading.hidden = section.innerHTML.trim().length > 0;
        errorEl.hidden = true;
        emptyEl.hidden = true;

        fetch(apiUrl)
            .then(function (r) {
                if (!r.ok) throw new Error("HTTP " + r.status);
                return r.json();
            })
            .then(function (payload) {
                renderPage(payload.prediction, payload.analysis, payload.history);
            })
            .catch(function (err) {
                loading.hidden = true;
                errorEl.hidden = false;
                errorMsg.textContent = err.message || "Errore nel caricamento dei dati.";
                section.setAttribute("aria-busy", "false");
            })
            .finally(function () {
                inFlight = false;
            });
    }

    loadData();
    setInterval(loadData, refreshSeconds * 1000);
})();
