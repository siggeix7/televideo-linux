(function () {
    "use strict";

    var body = document.body;
    var apiUrl = body.dataset.apiUrl;
    var refreshSeconds = Math.max(Number(body.dataset.refreshSeconds || 1200), 30);
    var svg = document.getElementById("chart-svg");
    var tooltip = document.getElementById("chart-tooltip");
    var crosshair = document.getElementById("chart-crosshair");
    var container = document.getElementById("chart-container");
    var emptyState = document.getElementById("chart-empty");
    var loadingEl = document.getElementById("chart-loading");
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
    var SVG_H = 520;
    var MARGIN = { top: 20, right: 16, bottom: 46, left: 72 };
    var PLOT_W = SVG_W - MARGIN.left - MARGIN.right;
    var PLOT_H = SVG_H - MARGIN.top - MARGIN.bottom;
    var DOT_R = 2.8;
    var DOT_R_HOVER = 5.5;

    function loadData() {
        if (loadingEl) loadingEl.hidden = false;
        if (container) container.hidden = true;
        if (emptyState) emptyState.hidden = true;

        fetch(apiUrl)
            .then(function (r) { return r.json(); })
            .then(function (payload) {
                draws = payload.draws || [];
                if (loadingEl) loadingEl.hidden = true;
                if (draws.length === 0) {
                    if (emptyState) emptyState.hidden = false;
                    if (container) container.hidden = true;
                    return;
                }
                if (emptyState) emptyState.hidden = true;
                if (container) container.hidden = false;
                viewRange = { start: 0, end: draws.length - 1 };
                render();
            })
            .catch(function () {
                if (loadingEl) loadingEl.hidden = true;
                if (emptyState) {
                    emptyState.hidden = false;
                    emptyState.querySelector("h2").textContent = "Errore caricamento";
                    emptyState.querySelector("p").textContent = "Impossibile caricare i dati montepremi.";
                }
            });
    }

    function formatEUR(value) {
        if (value == null) return "\u2014";
        var abs = Math.abs(value);
        if (abs >= 1e9) return "\u20ac" + (value / 1e9).toFixed(2) + "B";
        if (abs >= 1e6) return "\u20ac" + (value / 1e6).toFixed(1) + "M";
        if (abs >= 1e3) return "\u20ac" + (value / 1e3).toFixed(0) + "K";
        return "\u20ac" + value.toFixed(0);
    }

    function formatEURFull(value) {
        if (value == null) return "N/D";
        return value.toLocaleString("it-IT", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
    }

    function formatDate(iso) {
        if (!iso) return "";
        var parts = iso.split("-");
        if (parts.length === 3) {
            return parts[2] + "/" + parts[1] + "/" + parts[0].slice(2);
        }
        return iso;
    }

    function formatDateShort(iso) {
        if (!iso) return "";
        var parts = iso.split("-");
        if (parts.length === 3) return parts[2] + "/" + parts[1];
        return iso;
    }

    function visibleCount() {
        return Math.max(1, Math.ceil(viewRange.end) - Math.floor(viewRange.start) + 1);
    }

    function xScale(index) {
        if (draws.length <= 1) return MARGIN.left + PLOT_W / 2;
        var range = viewRange.end - viewRange.start || 1;
        return MARGIN.left + ((index - viewRange.start) / range) * PLOT_W;
    }

    function yScale(value, maxVal) {
        if (maxVal <= 0) return MARGIN.top + PLOT_H / 2;
        return MARGIN.top + PLOT_H - (value / maxVal) * PLOT_H;
    }

    function findSeriesMax(seriesKey) {
        var max = 0;
        for (var i = 0; i < draws.length; i++) {
            var v = draws[i][seriesKey];
            if (v != null && v > max) max = v;
        }
        return max;
    }

    function effectiveMax() {
        var max = 0;
        if (toggleJackpot.checked) max = Math.max(max, findSeriesMax("jackpot"));
        if (togglePrizePool.checked) max = Math.max(max, findSeriesMax("prize_pool"));
        return max || 1;
    }

    function niceMax(rawMax) {
        if (rawMax <= 0) return 1;
        var magnitude = Math.pow(10, Math.floor(Math.log10(rawMax)));
        var normalized = rawMax / magnitude;
        var nice;
        if (normalized <= 1) nice = 1;
        else if (normalized <= 2) nice = 2;
        else if (normalized <= 2.5) nice = 2.5;
        else if (normalized <= 5) nice = 5;
        else nice = 10;
        return nice * magnitude;
    }

    function buildYTicks(maxVal) {
        var nice = niceMax(maxVal);
        var tickCount = 5;
        var step = nice / tickCount;
        var ticks = [];
        for (var i = 0; i <= tickCount; i++) {
            ticks.push(step * i);
        }
        return ticks;
    }

    function buildLine(series, maxVal) {
        var path = "";
        var first = true;
        for (var i = 0; i < draws.length; i++) {
            var v = draws[i][series];
            if (v == null) continue;
            var x = xScale(i);
            var y = yScale(v, maxVal);
            if (first) { path += "M" + x.toFixed(1) + "," + y.toFixed(1); first = false; }
            else path += " L" + x.toFixed(1) + "," + y.toFixed(1);
        }
        return path;
    }

    function buildArea(series, maxVal) {
        var path = "";
        var first = true;
        var firstX = 0;
        var lastX = MARGIN.left + PLOT_W;
        for (var i = 0; i < draws.length; i++) {
            var v = draws[i][series];
            if (v == null) continue;
            var x = xScale(i);
            var y = yScale(v, maxVal);
            if (first) { firstX = x; path += "M" + x.toFixed(1) + "," + (MARGIN.top + PLOT_H).toFixed(1) + " L" + x.toFixed(1) + "," + y.toFixed(1); first = false; }
            else path += " L" + x.toFixed(1) + "," + y.toFixed(1);
            lastX = x;
        }
        if (!first) path += " L" + lastX.toFixed(1) + "," + (MARGIN.top + PLOT_H).toFixed(1) + " Z";
        return path;
    }

    function buildDots(series, maxVal) {
        var parts = [];
        for (var i = 0; i < draws.length; i++) {
            var v = draws[i][series];
            if (v == null) continue;
            var x = xScale(i);
            var y = yScale(v, maxVal);
            parts.push('<circle cx="' + x.toFixed(1) + '" cy="' + y.toFixed(1) + '" r="' + DOT_R + '" class="chart-dot chart-dot--' + (series === "prize_pool" ? "prize" : "jackpot") + '" data-idx="' + i + '"/>');
        }
        return parts.join("");
    }

    function buildXLabels() {
        var parts = [];
        var rangeSize = visibleCount();
        var labelEvery = Math.max(1, Math.round(rangeSize / 10));
        var start = Math.max(0, Math.floor(viewRange.start));
        var end = Math.min(draws.length - 1, Math.ceil(viewRange.end));

        // Use short format when many labels, long format when few
        var useShort = rangeSize > 200;
        var lastLabelX = -999;

        for (var i = start; i <= end; i += labelEvery) {
            if (!draws[i]) continue;
            var x = xScale(i);
            // Prevent overlapping labels
            if (x - lastLabelX < (useShort ? 40 : 62)) continue;
            lastLabelX = x;
            var label = useShort ? formatDateShort(draws[i].draw_date) : formatDate(draws[i].draw_date);
            parts.push('<text x="' + x.toFixed(1) + '" y="' + (SVG_H - 18) + '" class="chart-axis-label" text-anchor="middle">' + label + '</text>');
            parts.push('<line x1="' + x.toFixed(1) + '" y1="' + (MARGIN.top + PLOT_H) + '" x2="' + x.toFixed(1) + '" y2="' + (MARGIN.top + PLOT_H + 5) + '" stroke="rgba(0,255,0,0.15)" stroke-width="0.5"/>');
        }
        return parts.join("");
    }

    function buildGrid(yTicks, maxVal) {
        var parts = [];
        for (var ti = 0; ti < yTicks.length; ti++) {
            var y = yScale(yTicks[ti], maxVal);
            // Major grid lines
            if (ti % 5 === 0 || ti === yTicks.length - 1) {
                parts.push('<line x1="' + MARGIN.left + '" y1="' + y.toFixed(1) + '" x2="' + (MARGIN.left + PLOT_W) + '" y2="' + y.toFixed(1) + '" class="chart-grid chart-grid--major"/>');
            } else {
                parts.push('<line x1="' + MARGIN.left + '" y1="' + y.toFixed(1) + '" x2="' + (MARGIN.left + PLOT_W) + '" y2="' + y.toFixed(1) + '" class="chart-grid chart-grid--minor"/>');
            }
            parts.push('<text x="' + (MARGIN.left - 8) + '" y="' + (y + 4).toFixed(1) + '" class="chart-axis-label" text-anchor="end">' + formatEUR(yTicks[ti]) + '</text>');
        }
        return parts.join("");
    }

    function findDrawAtX(mx) {
        var best = -1;
        var bestDist = 48;
        for (var i = 0; i < draws.length; i++) {
            var x = xScale(i);
            var dist = Math.abs(x - mx);
            if (dist < bestDist) { bestDist = dist; best = i; }
        }
        return best;
    }

    function render() {
        var maxVal = effectiveMax();
        var showJackpot = toggleJackpot.checked;
        var showPrize = togglePrizePool.checked;
        var yTicks = buildYTicks(maxVal);

        var html = '<g class="chart-layer">';

        // Plot background
        html += '<rect x="' + MARGIN.left + '" y="' + MARGIN.top + '" width="' + PLOT_W + '" height="' + PLOT_H + '" fill="rgba(0,40,10,0.18)" rx="2"/>';

        // Grid
        html += buildGrid(yTicks, maxVal);

        // Axes
        html += '<line x1="' + MARGIN.left + '" y1="' + MARGIN.top + '" x2="' + MARGIN.left + '" y2="' + (MARGIN.top + PLOT_H) + '" class="chart-axis"/>';
        html += '<line x1="' + MARGIN.left + '" y1="' + (MARGIN.top + PLOT_H) + '" x2="' + (MARGIN.left + PLOT_W) + '" y2="' + (MARGIN.top + PLOT_H) + '" class="chart-axis"/>';

        // Y-axis title
        html += '<text x="' + (MARGIN.left - 62) + '" y="' + (MARGIN.top - 10) + '" class="chart-axis-title" text-anchor="start">EUR</text>';

        // Area fills
        if (showJackpot) {
            html += '<path d="' + buildArea("jackpot", maxVal) + '" class="chart-area chart-area--jackpot"/>';
        }
        if (showPrize) {
            html += '<path d="' + buildArea("prize_pool", maxVal) + '" class="chart-area chart-area--prize"/>';
        }

        // Lines
        if (showJackpot) {
            html += '<path d="' + buildLine("jackpot", maxVal) + '" class="chart-line chart-line--jackpot"/>';
        }
        if (showPrize) {
            html += '<path d="' + buildLine("prize_pool", maxVal) + '" class="chart-line chart-line--prize"/>';
        }

        // Dots
        if (showJackpot) html += buildDots("jackpot", maxVal);
        if (showPrize) html += buildDots("prize_pool", maxVal);

        // X-axis labels
        html += buildXLabels();

        // Visible range indicator
        var rangePercent = Math.round((visibleCount() / draws.length) * 100);
        html += '<text x="' + (MARGIN.left + PLOT_W) + '" y="' + (MARGIN.top - 6) + '" class="chart-axis-label" text-anchor="end">' + rangePercent + '% visibile</text>';

        html += '</g>';

        svg.innerHTML = html;
    }

    // ── Crosshair ──────────────────────────────────────────────

    function updateCrosshair(idx, evt) {
        if (idx < 0 || idx >= draws.length) {
            crosshair.hidden = true;
            return;
        }
        var draw = draws[idx];
        var rect = svg.getBoundingClientRect();
        var scaleX = SVG_W / rect.width;
        var scaleY = SVG_H / rect.height;
        var svgX = (evt.clientX - rect.left) * scaleX;
        var svgY = (evt.clientY - rect.top) * scaleY;
        var dotX = xScale(idx);
        var maxVal = effectiveMax();

        crosshair.innerHTML =
            '<line x1="' + dotX.toFixed(1) + '" y1="' + MARGIN.top + '" x2="' + dotX.toFixed(1) + '" y2="' + (MARGIN.top + PLOT_H) + '" class="chart-crosshair-line"/>' +
            '<circle cx="' + dotX.toFixed(1) + '" cy="' + (MARGIN.top + 2) + '" r="3" class="chart-crosshair-handle"/>';
        crosshair.hidden = false;

        // Tooltip
        tooltip.innerHTML =
            '<strong>' + formatDate(draw.draw_date) + '</strong> <em>N.' + draw.draw_number + '</em>' +
            '<div class="chart-tooltip__values">' +
            '<span class="chart-tooltip--jackpot">\u2605 Jackpot ' + formatEURFull(draw.jackpot) + '</span>' +
            '<span class="chart-tooltip--prize">\u25C6 Montepremi ' + formatEURFull(draw.prize_pool) + '</span>' +
            '</div>';
        tooltip.hidden = false;

        var tx = svgX + 18;
        var ty = svgY - 16;
        if (tx + 220 > SVG_W) tx = svgX - 240;
        if (ty < 10) ty = svgY + 24;
        if (ty > SVG_H - 100) ty = SVG_H - 100;
        tooltip.style.left = (tx / SVG_W * 100) + "%";
        tooltip.style.top = (ty / SVG_H * 100) + "%";
    }

    function getEventSVGPos(evt) {
        var rect = svg.getBoundingClientRect();
        return (evt.clientX - rect.left) * (SVG_W / rect.width);
    }

    svg.addEventListener("mousemove", function (evt) {
        var mx = getEventSVGPos(evt);
        var idx = findDrawAtX(mx);
        updateCrosshair(idx, evt);
        evt.stopPropagation();
    });

    svg.addEventListener("mouseleave", function () {
        tooltip.hidden = true;
        if (crosshair) crosshair.hidden = true;
    });

    // ── Drag to pan ────────────────────────────────────────────

    svg.addEventListener("mousedown", function (evt) {
        isDragging = true;
        dragStart = getEventSVGPos(evt);
        dragRangeStart = viewRange.start;
        svg.style.cursor = "grabbing";
        tooltip.hidden = true;
        if (crosshair) crosshair.hidden = true;
        evt.preventDefault();
    });

    svg.addEventListener("touchstart", function (evt) {
        if (evt.touches.length === 1) {
            isDragging = true;
            dragStart = getEventSVGPos(evt);
            dragRangeStart = viewRange.start;
            tooltip.hidden = true;
            if (crosshair) crosshair.hidden = true;
            evt.preventDefault();
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
        var mx = getEventSVGPos(evt);
        var dx = mx - dragStart;
        var range = viewRange.end - viewRange.start;
        var shift = -(dx / PLOT_W) * range;
        var newStart = Math.max(0, Math.min(draws.length - 1 - range, dragRangeStart + shift));
        viewRange.start = newStart;
        viewRange.end = newStart + range;
        render();
    });

    document.addEventListener("mouseup", function () { isDragging = false; svg.style.cursor = "crosshair"; });
    document.addEventListener("touchend", function () { isDragging = false; });

    // ── Scroll-wheel zoom ──────────────────────────────────────

    svg.addEventListener("wheel", function (evt) {
        evt.preventDefault();
        var mx = getEventSVGPos(evt);
        var dataX = viewRange.start + ((mx - MARGIN.left) / PLOT_W) * (viewRange.end - viewRange.start);
        var factor = evt.deltaY > 0 ? 1.35 : 0.74;
        var halfRange = (viewRange.end - viewRange.start) / 2 * factor;
        halfRange = Math.max(0.5, halfRange);
        viewRange.start = Math.max(0, dataX - halfRange);
        viewRange.end = Math.min(draws.length - 1, dataX + halfRange);
        if (viewRange.end - viewRange.start < 1) {
            viewRange.start = Math.max(0, dataX - 0.5);
            viewRange.end = Math.min(draws.length - 1, dataX + 0.5);
        }
        render();
        if (crosshair) crosshair.hidden = true;
        tooltip.hidden = true;
    }, { passive: false });

    // ── Keyboard ────────────────────────────────────────────────

    svg.setAttribute("tabindex", "0");
    svg.setAttribute("role", "img");
    svg.addEventListener("keydown", function (evt) {
        var range = viewRange.end - viewRange.start;
        var step = range / 10;
        if (evt.key === "ArrowLeft") {
            evt.preventDefault();
            viewRange.start = Math.max(0, viewRange.start - step);
            viewRange.end = Math.max(1, viewRange.end - step);
            render();
        }
        if (evt.key === "ArrowRight") {
            evt.preventDefault();
            viewRange.start = Math.min(draws.length - 1 - range, viewRange.start + step);
            viewRange.end = Math.min(draws.length - 1, viewRange.end + step);
            render();
        }
        if (evt.key === "+" || evt.key === "=") { zoomInBtn.click(); }
        if (evt.key === "-") { zoomOutBtn.click(); }
        if (evt.key === "0" || evt.key === "Escape") { zoomResetBtn.click(); }
    });

    // ── Zoom buttons ───────────────────────────────────────────

    zoomInBtn.addEventListener("click", function () {
        var center = (viewRange.start + viewRange.end) / 2;
        var halfRange = (viewRange.end - viewRange.start) / 2 * 0.6;
        halfRange = Math.max(0.5, halfRange);
        viewRange.start = Math.max(0, center - halfRange);
        viewRange.end = Math.min(draws.length - 1, center + halfRange);
        if (viewRange.end - viewRange.start < 1) {
            viewRange.start = Math.max(0, center - 0.5);
            viewRange.end = Math.min(draws.length - 1, center + 0.5);
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

    // ── Toggle series ──────────────────────────────────────────

    toggleJackpot.addEventListener("change", render);
    togglePrizePool.addEventListener("change", render);

    // ── Init ───────────────────────────────────────────────────

    loadData();
    setInterval(function () {
        if (!isDragging) loadData();
    }, refreshSeconds * 1000);
})();
