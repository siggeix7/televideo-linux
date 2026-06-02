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

    function numberChip(value, cls) {
        var chip = document.createElement("span");
        chip.className = "number-chip" + (cls ? " " + cls : "");
        chip.textContent = value;
        return chip;
    }

    function numberChipSmall(value, cls) {
        var chip = document.createElement("span");
        chip.className = "number-chip number-chip--small" + (cls ? " " + cls : "");
        chip.textContent = value;
        return chip;
    }

    function renderComboCard(combo, idx) {
        var html = '<article class="prediction-card' + (idx === 0 ? ' prediction-card--featured' : '') + '">';
        html += '<header class="prediction-card__header">';
        html += '<h2 class="prediction-card__title">' + (combo.label || 'Combinazione ' + (idx + 1)) + '</h2>';
        html += '<p class="prediction-card__desc">' + (combo.description || '') + '</p>';
        html += '</header>';

        // Numbers row
        html += '<div class="number-row prediction-card__numbers">';
        (combo.numbers || []).forEach(function (n) {
            html += '<span class="number-chip">' + n + '</span>';
        });
        html += '</div>';

        // Jolly and SuperStar
        html += '<dl class="prediction-card__extras">';
        html += '<div><dt>Jolly</dt><dd><span class="number-chip number-chip--small">' + (combo.jolly || '-') + '</span></dd></div>';
        html += '<div><dt>SuperStar</dt><dd><span class="number-chip number-chip--small number-chip--special">' + (combo.superstar || '-') + '</span></dd></div>';
        html += '</dl>';

        // Reasoning section
        if (combo.reasoning && combo.reasoning.length > 0) {
            html += '<details class="prediction-card__reasoning">';
            html += '<summary>Metodologia</summary>';
            html += '<ul>';
            combo.reasoning.forEach(function (r) {
                html += '<li>' + r + '</li>';
            });
            html += '</ul>';
            if (combo.cycle_details && combo.cycle_details.length > 0) {
                html += '<p class="prediction-card__details-label">Dettaglio cicli:</p>';
                html += '<ul>';
                combo.cycle_details.forEach(function (d) {
                    html += '<li>' + d + '</li>';
                });
                html += '</ul>';
            }
            if (combo.gap_details && combo.gap_details.length > 0) {
                html += '<p class="prediction-card__details-label">Dettaglio gap:</p>';
                html += '<ul>';
                combo.gap_details.forEach(function (d) {
                    html += '<li>' + d + '</li>';
                });
                html += '</ul>';
            }
            if (combo.context) {
                html += '<p class="prediction-card__context">' + combo.context + '</p>';
            }
            html += '</details>';
        }

        html += '</article>';
        return html;
    }

    function renderAnalysis(analysis) {
        if (!analysis) return '';

        var html = '<section class="analysis-section">';
        html += '<h2 class="analysis-section__title">Analisi statistica</h2>';

        // Last draw
        if (analysis.last_draw) {
            html += '<div class="analysis-block">';
            html += '<h3>Ultima estrazione</h3>';
            html += '<p><strong>' + analysis.last_draw.date + '</strong>: ';
            (analysis.last_draw.numbers || []).forEach(function (n) {
                html += '<span class="number-chip number-chip--small">' + n + '</span>';
            });
            html += ' <span class="analysis-note">(somma: ' + analysis.last_draw.sum + ')</span>';
            html += '</p>';
            html += '</div>';
        }

        // Most overdue
        if (analysis.most_overdue && analysis.most_overdue.length > 0) {
            html += '<div class="analysis-block">';
            html += '<h3>Numeri pi\u00f9 in ritardo</h3>';
            html += '<table class="analysis-table">';
            html += '<thead><tr><th>Numero</th><th>Gap attuale</th><th>Ciclo medio</th><th>Rapporto</th></tr></thead>';
            html += '<tbody>';
            analysis.most_overdue.forEach(function (item) {
                var n = item[0], gap = item[1], avg = item[2], ratio = item[3];
                html += '<tr><td><strong>' + n + '</strong></td><td>' + gap + ' estr.</td><td>' + (avg || '-') + '</td><td>' + ratio + 'x</td></tr>';
            });
            html += '</tbody></table>';
            html += '</div>';
        }

        // Trending up
        if (analysis.trending_up && analysis.trending_up.length > 0) {
            html += '<div class="analysis-block">';
            html += '<h3>Numeri in tendenza crescente</h3>';
            html += '<p class="analysis-note">Numeri con frequenza recente superiore alla media storica (ultime 100 vs totale)</p>';
            html += '<div class="analysis-trends">';
            analysis.trending_up.forEach(function (item) {
                html += '<span class="number-chip number-chip--small number-chip--trend">' + item[0] + ' (+' + item[1] + ')</span>';
            });
            html += '</div>';
            html += '</div>';
        }

        // Methodology comparison
        if (analysis.methodology) {
            html += '<details class="analysis-block analysis-methodology">';
            html += '<summary><h3 style="display:inline">Metodologia e performance</h3></summary>';
            html += '<table class="analysis-table">';
            html += '<thead><tr><th>Strategia</th><th>Performance media</th></tr></thead>';
            html += '<tbody>';
            Object.keys(analysis.methodology).forEach(function (key) {
                var m = analysis.methodology[key];
                html += '<tr><td><strong>' + key + '</strong><br><span class="analysis-note">' + m.description + '</span></td><td>' + m.avg_performance + '</td></tr>';
            });
            html += '</tbody></table>';
            html += '<p class="analysis-note">Baseline casuale: ' + analysis.random_baseline + ' match/estrazione (6/90). Solo il ciclo di ritorno mostra significativit\u00e0 statistica (p&lt;0.05) su 2809 backtest.</p>';
            html += '</details>';
        }

        html += '</section>';
        return html;
    }

    function renderPrediction(prediction, analysis) {
        if (!prediction || !prediction.combinations || prediction.combinations.length === 0) {
            emptyEl.hidden = false;
            loading.hidden = true;
            return;
        }

        loading.hidden = true;
        emptyEl.hidden = true;

        var html = '<div class="prediction-header">';
        if (prediction.target_draw_date) {
            html += '<p class="status-label">Pronostico per il concorso N.' + (prediction.draw_number || '?') + ' del ' + prediction.target_draw_date + '</p>';
        }
        if (prediction.created_at) {
            html += '<p class="prediction-date">Generato il ' + prediction.created_at.slice(0, 16).replace("T", " ") + '</p>';
        }
        html += '</div>';

        html += '<div class="prediction-combos">';
        prediction.combinations.forEach(function (combo, idx) {
            html += renderComboCard(combo, idx);
        });
        html += '</div>';

        // Analysis section
        html += renderAnalysis(analysis);

        // Methodology info (collapsible)
        html += '<details class="prediction-info">';
        html += '<summary>Come funziona Fanta-Super</summary>';
        html += '<div class="prediction-info__body">';
        html += '<p>Le 6 combinazioni sono generate da un motore predittivo che analizza lo storico completo delle estrazioni SuperEnalotto (dal 2009) con quattro strategie complementari:</p>';
        html += '<ul>';
        html += '<li><strong>Ciclo di ritorno</strong>: ogni numero ha un ritmo tipico di riapparizione (~13-18 estrazioni). Quando il gap attuale si avvicina alla media, la probabilit\u00e0 aumenta leggermente. <em>Unica strategia con significativit\u00e0 statistica (p&lt;0.05).</em></li>';
        html += '<li><strong>Catena di Markov</strong>: analizza quali numeri seguono pi\u00f9 frequentemente quelli dell\'ultima estrazione, usando una finestra di 1000 estrazioni.</li>';
        html += '<li><strong>Ritardatari</strong>: numeri con il gap attuale pi\u00f9 lungo, confrontato con il loro ciclo storico medio.</li>';
        html += '<li><strong>Numeri caldi</strong>: frequenza nelle ultime 50 estrazioni.</li>';
        html += '<li><strong>Bilanciato</strong>: mix delle strategie distribuito sulle decine.</li>';
        html += '<li><strong>Ensemble</strong>: combinazione pesata di tutte le strategie, con peso proporzionale all\'affidabilit\u00e0 nei backtest.</li>';
        html += '</ul>';
        html += '<p><strong>Nota:</strong> Il SuperEnalotto \u00e8 un gioco casuale. La baseline teorica \u00e8 0.40 match a estrazione. Nessuna strategia pu\u00f2 garantire vincite. I pronostici vengono ricalcolati automaticamente dopo ogni nuova estrazione.</p>';
        html += '</div>';
        html += '</details>';

        section.innerHTML = html;
    }

    function renderHistory(history) {
        if (!history || history.length === 0) return;

        var container = document.getElementById("prediction-history") || document.createElement("section");
        container.id = "prediction-history";
        container.className = "prediction-history";

        var html = '<h2 class="prediction-history__title">Storico pronostici verificati</h2>';
        html += '<div class="prediction-history__list">';

        history.forEach(function (pred) {
            html += '<article class="prediction-history__item">';
            html += '<div class="prediction-history__header">';
            html += '<strong>Pronostico del ' + pred.created_at.slice(0, 10) + '</strong>';
            html += '<span>per concorso N.' + pred.draw_number + ' del ' + pred.target_draw_date + '</span>';
            html += '</div>';
            html += '<div class="prediction-history__combos">';
            (pred.combinations || []).forEach(function (combo, idx) {
                var mc = pred.matched_counts && pred.matched_counts[idx];
                var matchCount = mc ? mc.matches : 0;
                var jollyOk = mc && mc.jolly_match;
                var ssOk = mc && mc.superstar_match;

                html += '<div class="prediction-history__combo' + (matchCount > 0 ? ' has-match' : '') + '">';
                html += '<span class="prediction-history__label">' + (combo.label || 'C' + (idx + 1)) + '</span>';
                html += '<span class="prediction-history__nums">';
                (combo.numbers || []).forEach(function (n) {
                    html += '<span class="number-chip number-chip--small' + (matchCount > 0 ? ' number-chip--hit' : ' number-chip--miss') + '">' + n + '</span>';
                });
                html += '</span>';
                html += '<span class="prediction-history__match">' + matchCount + ' num';
                if (jollyOk) html += ' + Jolly';
                if (ssOk) html += ' + SuperStar';
                html += '</span>';
                html += '</div>';
            });
            html += '</div>';
            html += '</article>';
        });

        html += '</div>';
        container.innerHTML = html;
        section.appendChild(container);
    }

    function loadData() {
        loading.hidden = false;
        errorEl.hidden = true;
        emptyEl.hidden = true;

        fetch(apiUrl)
            .then(function (r) { return r.json(); })
            .then(function (payload) {
                renderPrediction(payload.prediction, payload.analysis);
                renderHistory(payload.history);
            })
            .catch(function (err) {
                loading.hidden = true;
                errorEl.hidden = false;
                errorMsg.textContent = err.message || "Errore caricamento";
            });
    }

    loadData();
    setInterval(loadData, refreshSeconds * 1000);
})();
