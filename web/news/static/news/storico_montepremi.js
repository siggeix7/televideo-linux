(function () {
    "use strict";

    var body = document.body;
    var apiUrl = body.dataset.apiUrl;
    var refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 60), 15);
    var svg = document.getElementById("chart-svg");
    var tooltip = document.getElementById("chart-tooltip");
    var container = document.getElementById("chart-container");
    var emptyState = document.getElementById("chart-empty");
    var toggleJackpot = document.getElementById("toggle-jackpot");
    var togglePrizePool = document.getElementById("toggle-prize-pool");
    var zoomInBtn = document.getElementById("zoom-in");
    var zoomOutBtn = document.getElementById("zoom-out");
    var zoomResetBtn = document.getElementById("zoom-reset");

    var draws = [];
    var viewRange = { start: 0, end: 1 };
    var isDragging = false;
    var dragStart = 0;
    var dragRangeStart = 0;
    var SVG_W = 960;
    var SVG_H = 500;
    var MARGIN = { top: 30, right: 40, bottom: 50, left: 80 };
    var PLOT_W = SVG_W - MARGIN.left - MARGIN.right;
    var PLOT_H = SVG_H - MARGIN.top - MARGIN.bottom;

    function loadData() {
        fetch(apiUrl)
            .then(function (r) { return r.json(); })
            .then(function (payload) {
                draws = payload.draws || [];
                if (draws.length === 0) {
                    emptyState.hidden = false;
                    container.hidden = true;
                    return;
                }
                emptyState.hidden = true;
                container.hidden = false;
                viewRange = { start: 0, end: draws.length - 1 };
                render();
            })
            .catch(function () {
                emptyState.hidden = false;
                emptyState.querySelector("h2").textContent = "Errore caricamento";
                emptyState.querySelector("p").textContent = "Impossibile caricare i dati montepremi.";
            });
    }

    function formatEUR(value) {
        if (value == null) return "N/D";
        var millions = value / 1e6;
        if (millions >= 1) {
            return millions.toFixed(1) + " M";
        }
        var thousands = value / 1e3;
        if (thousands >= 1) {
            return thousands.toFixed(0) + " K";
        }
        return value.toFixed(0);
    }

    function formatEURFull(value) {
        if (value == null) return "N/D";
        return value.toLocaleString("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
    }

    function xScale(index) {
        if (draws.length <= 1) return MARGIN.left + PLOT_W / 2;
        var range = viewRange.end - viewRange.start || 1;
        return MARGIN.left + ((index - viewRange.start) / range) * PLOT_W;
    }

    function yScale(value, maxVal) {
        if (maxVal === 0) return MARGIN.top + PLOT_H / 2;
        return MARGIN.top + PLOT_H - (value / maxVal) * PLOT_H;
    }

    function findMax(series) {
        var max = 0;
        for (var i = 0; i < draws.length; i++) {
            var v = series === "jackpot" ? draws[i].jackpot : draws[i].prize_pool;
            if (v != null && v > max) max = v;
        }
        return max;
    }

    function buildLine(draws, series, maxVal) {
        var path = "";
        var first = true;
        for (var i = 0; i < draws.length; i++) {
            var v = series === "jackpot" ? draws[i].jackpot : draws[i].prize_pool;
            if (v == null) continue;
            var x = xScale(i);
            var y = yScale(v, maxVal);
            if (first) {
                path += "M" + x.toFixed(1) + "," + y.toFixed(1);
                first = false;
            } else {
                path += " L" + x.toFixed(1) + "," + y.toFixed(1);
            }
        }
        return path;
    }

    function buildDotsPath(series) {
        var maxVal = findMax(series);
        var parts = [];
        for (var i = 0; i < draws.length; i++) {
            var v = series === "jackpot" ? draws[i].jackpot : draws[i].prize_pool;
            if (v == null) continue;
            var x = xScale(i);
            var y = yScale(v, maxVal);
            parts.push('<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="3" class="chart-dot chart-dot--' + series + '" data-idx="' + i + '"/>');
        }
        return parts.join("");
    }

    function buildYTicks(maxVal) {
        var ticks = [];
        var step = Math.pow(10, Math.floor(Math.log10(maxVal || 1)));
        var count = 5;
        for (var i = 0; i <= count; i++) {
            var v = (maxVal / count) * i;
            ticks.push(v);
        }
        return ticks;
    }

    function buildXLabels() {
        var parts = [];
        var start = Math.max(0, Math.floor(viewRange.start));
        var end = Math.min(draws.length - 1, Math.ceil(viewRange.end));
        var step = Math.max(1, Math.floor((end - start) / 10));
        for (var i = start; i <= end; i += step) {
            var x = xScale(i);
            var date = draws[i] ? draws[i].draw_date : "";
            var label = date ? date.slice(0, 7) : "";
            parts.push('<text x="' + x.toFixed(1) + '" y="' + (SVG_H - 10) + '" class="chart-axis-label" text-anchor="middle">' + label + '</text>');
        }
        return parts.join("");
    }

    function findDrawAtX(mx) {
        var best = -1;
        var bestDist = Infinity;
        for (var i = 0; i < draws.length; i++) {
            var x = xScale(i);
            var dist = Math.abs(x - mx);
            if (dist < bestDist && dist < 30) {
                bestDist = dist;
                best = i;
            }
        }
        return best;
    }

    function render() {
        var jackpotMax = findMax("jackpot");
        var prizeMax = findMax("prize_pool");
        var combinedMax = Math.max(jackpotMax, prizeMax);
        if (combinedMax === 0) combinedMax = 1;

        var showJackpot = toggleJackpot.checked;
        var showPrize = togglePrizePool.checked;

        var yTicks = buildYTicks(showJackpot ? jackpotMax : (showPrize ? prizeMax : combinedMax));
        if (showJackpot && showPrize) yTicks = buildYTicks(combinedMax);

        var html = '<g>';

        html += '<rect x="' + MARGIN.left + '" y="' + MARGIN.top + '" width="' + PLOT_W + '" height="' + PLOT_H + '" fill="rgba(0,255,0,0.03)" stroke="rgba(0,255,0,0.15)" stroke-width="1"/>';

        html += '<line x1="' + MARGIN.left + '" y1="' + MARGIN.top + '" x2="' + MARGIN.left + '" y2="' + (MARGIN.top + PLOT_H) + '" class="chart-axis" stroke="rgba(0,255,0,0.35)" stroke-width="1.5"/>';
        html += '<line x1="' + MARGIN.left + '" y1="' + (MARGIN.top + PLOT_H) + '" x2="' + (MARGIN.left + PLOT_W) + '" y2="' + (MARGIN.top + PLOT_H) + '" class="chart-axis" stroke="rgba(0,255,0,0.35)" stroke-width="1.5"/>';

        for (var ti = 0; ti < yTicks.length; ti++) {
            var tickVal = yTicks[ti];
            var y = yScale(tickVal, combinedMax);
            html += '<line x1="' + MARGIN.left + '" y1="' + y.toFixed(1) + '" x2="' + (MARGIN.left + PLOT_W) + '" y2="' + y.toFixed(1) + '" stroke="rgba(0,255,0,0.08)" stroke-width="0.5"/>';
            html += '<text x="' + (MARGIN.left - 8) + '" y="' + (y + 4).toFixed(1) + '" class="chart-axis-label" text-anchor="end">' + formatEUR(tickVal) + '</text>';
        }

        html += buildXLabels();

        if (showJackpot) {
            html += '<path d="' + buildLine(draws, "jackpot", combinedMax) + '" fill="none" class="chart-line chart-line--jackpot"/>';
            html += buildDotsPath("jackpot");
        }
        if (showPrize) {
            html += '<path d="' + buildLine(draws, "prize_pool", combinedMax) + '" fill="none" class="chart-line chart-line--prize"/>';
            html += buildDotsPath("prize");
        }

        html += '</g>';

        svg.innerHTML = html;
    }

    function showTooltip(idx, evt) {
        if (idx < 0 || idx >= draws.length) {
            tooltip.hidden = true;
            return;
        }
        var draw = draws[idx];
        var rect = svg.getBoundingClientRect();
        var scaleX = SVG_W / rect.width;
        var scaleY = SVG_H / rect.height;
        var svgX = (evt.clientX - rect.left) * scaleX;
        var svgY = (evt.clientY - rect.top) * scaleY;

        tooltip.innerHTML =
            '<strong>' + draw.draw_date + '</strong> (N.' + draw.draw_number + ')' +
            '<br>Jackpot: <span class="chart-tooltip--jackpot">' + formatEURFull(draw.jackpot) + '</span>' +
            '<br>Montepremi: <span class="chart-tooltip--prize">' + formatEURFull(draw.prize_pool) + '</span>';
        tooltip.hidden = false;

        var tx = svgX + 16;
        var ty = svgY - 10;
        if (tx + 200 > SVG_W) tx = svgX - 210;
        if (ty < 0) ty = svgY + 20;
        tooltip.style.left = (tx / SVG_W * 100) + "%";
        tooltip.style.top = (ty / SVG_H * 100) + "%";
    }

    function getEventSVGPos(evt) {
        var rect = svg.getBoundingClientRect();
        var scaleX = SVG_W / rect.width;
        return (evt.clientX - rect.left) * scaleX;
    }

    svg.addEventListener("mousemove", function (evt) {
        var mx = getEventSVGPos(evt);
        var idx = findDrawAtX(mx);
        showTooltip(idx, evt);
    });

    svg.addEventListener("mouseleave", function () {
        tooltip.hidden = true;
    });

    svg.addEventListener("mousedown", function (evt) {
        isDragging = true;
        dragStart = getEventSVGPos(evt);
        dragRangeStart = viewRange.start;
        svg.style.cursor = "grabbing";
        evt.preventDefault();
    });

    svg.addEventListener("touchstart", function (evt) {
        if (evt.touches.length === 1) {
            isDragging = true;
            dragStart = evt.touches[0].clientX;
            dragRangeStart = viewRange.start;
        }
    }, { passive: false });

    document.addEventListener("mousemove", function (evt) {
        if (!isDragging) return;
        var mx = getEventSVGPos(evt);
        var dx = mx - dragStart;
        var range = viewRange.end - viewRange.start;
        var shift = -(dx / PLOT_W) * range;
        var newStart = Math.max(0, Math.min(draws.length - 1 - range, dragRangeStart + shift));
        viewRange.start = newStart;
        viewRange.end = newStart + range;
        render();
    });

    document.addEventListener("touchmove", function (evt) {
        if (!isDragging) return;
        var dx = (evt.touches[0].clientX - dragStart) / (svg.getBoundingClientRect().width || 1) * SVG_W;
        var range = viewRange.end - viewRange.start;
        var shift = -(dx / PLOT_W) * range;
        var newStart = Math.max(0, Math.min(draws.length - 1 - range, dragRangeStart + shift));
        viewRange.start = newStart;
        viewRange.end = newStart + range;
        render();
    });

    document.addEventListener("mouseup", function () {
        isDragging = false;
        svg.style.cursor = "";
    });
    document.addEventListener("touchend", function () {
        isDragging = false;
    });

    zoomInBtn.addEventListener("click", function () {
        var center = (viewRange.start + viewRange.end) / 2;
        var halfRange = (viewRange.end - viewRange.start) / 2 * 0.6;
        viewRange.start = Math.max(0, center - halfRange);
        viewRange.end = Math.min(draws.length - 1, center + halfRange);
        if (viewRange.end - viewRange.start < 2) {
            viewRange.start = Math.max(0, center - 1);
            viewRange.end = Math.min(draws.length - 1, center + 1);
        }
        render();
    });

    zoomOutBtn.addEventListener("click", function () {
        var center = (viewRange.start + viewRange.end) / 2;
        var halfRange = (viewRange.end - viewRange.start) / 2 * 1.8;
        viewRange.start = Math.max(0, center - halfRange);
        viewRange.end = Math.min(draws.length - 1, center + halfRange);
        render();
    });

    zoomResetBtn.addEventListener("click", function () {
        viewRange = { start: 0, end: draws.length - 1 };
        render();
    });

    toggleJackpot.addEventListener("change", render);
    togglePrizePool.addEventListener("change", render);

    loadData();
    setInterval(function () {
        if (!isDragging) loadData();
    }, refreshSeconds * 1000);
})();
