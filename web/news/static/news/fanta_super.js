(function () {
    "use strict";

    var body = document.body;
    var apiUrl = body.dataset.apiUrl;
    var refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
    var section = document.getElementById("prediction-section");
    var loading = document.getElementById("prediction-loading");
    var empty = document.getElementById("prediction-empty");
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

    function renderPrediction(prediction) {
        if (!prediction || !prediction.combinations || prediction.combinations.length === 0) {
            empty.hidden = false;
            loading.hidden = true;
            return;
        }

        loading.hidden = true;
        empty.hidden = true;

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
            html += '<article class="prediction-card' + (idx === 0 ? ' prediction-card--featured' : '') + '">';
            html += '<header class="prediction-card__header">';
            html += '<h2 class="prediction-card__title">' + (combo.label || 'Combinazione ' + (idx + 1)) + '</h2>';
            html += '<p class="prediction-card__desc">' + (combo.description || '') + '</p>';
            html += '</header>';
            html += '<div class="number-row prediction-card__numbers">';
            (combo.numbers || []).forEach(function (n) {
                html += '<span class="number-chip">' + n + '</span>';
            });
            html += '</div>';
            html += '<dl class="prediction-card__extras">';
            html += '<div><dt>Jolly</dt><dd><span class="number-chip number-chip--small">' + (combo.jolly || '-') + '</span></dd></div>';
            html += '<div><dt>SuperStar</dt><dd><span class="number-chip number-chip--small number-chip--special">' + (combo.superstar || '-') + '</span></dd></div>';
            html += '</dl>';
            html += '</article>';
        });
        html += '</div>';

        var infoHtml = '';
        infoHtml += '<details class="prediction-info">';
        infoHtml += '<summary>Come vengono calcolati i pronostici</summary>';
        infoHtml += '<div class="prediction-info__body">';
        infoHtml += '<p>I pronostici sono generati analizzando lo storico completo delle estrazioni SuperEnalotto con metodi statistici:</p>';
        infoHtml += '<ul>';
        infoHtml += '<li><strong>Numeri caldi</strong>: i piu frequenti nelle ultime 50 estrazioni</li>';
        infoHtml += '<li><strong>Numeri freddi</strong>: i meno frequenti nell&apos;intero storico</li>';
        infoHtml += '<li><strong>Bilanciato</strong>: mix di caldi e freddi distribuiti su decine diverse</li>';
        infoHtml += '<li><strong>Pattern</strong>: sequenze e pattern statistici delle estrazioni passate</li>';
        infoHtml += '<li><strong>Ritardatari</strong>: i numeri che mancano da piu tempo</li>';
        infoHtml += '<li><strong>Probabilistico</strong>: pesato sulla frequenza inversa di ciascun numero</li>';
        infoHtml += '</ul>';
        infoHtml += '<p>I pronostici vengono ricalcolati automaticamente dopo ogni nuova estrazione.</p>';
        infoHtml += '</div>';
        infoHtml += '</details>';

        section.innerHTML = html + infoHtml;
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
        empty.hidden = true;

        fetch(apiUrl)
            .then(function (r) { return r.json(); })
            .then(function (payload) {
                renderPrediction(payload.prediction);
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
