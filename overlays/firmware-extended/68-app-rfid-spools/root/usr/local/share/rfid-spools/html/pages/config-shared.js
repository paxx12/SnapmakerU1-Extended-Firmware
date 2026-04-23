'use strict';

// ── Shared config page constants & helpers ───────────────────────────────────

var ConfigShared = (function () {

    var DEFAULT_NAMES = [
        'Slot 1 (Top-Left)',
        'Slot 2 (Bottom-Left)',
        'Slot 3 (Top-Right)',
        'Slot 4 (Bottom-Right)'
    ];

    var GENERIC_FIELDS = [
        { value: 'manufacturer',       label: 'Manufacturer' },
        { value: 'type',               label: 'Material Type' },
        { value: 'modifiers',          label: 'Modifiers / Subtype' },
        { value: 'color',              label: 'Color' },
        { value: 'hotend_min_temp',    label: 'Nozzle Min Temp' },
        { value: 'hotend_max_temp',    label: 'Nozzle Max Temp' },
        { value: 'bed_temp_min',       label: 'Bed Temp Min' },
        { value: 'bed_temp_max',       label: 'Bed Temp Max' },
        { value: 'diameter_mm',        label: 'Diameter (mm)' },
        { value: 'weight_grams',       label: 'Weight (g)' },
        { value: 'drying_temp',        label: 'Drying Temp' },
        { value: 'drying_time',        label: 'Drying Time (h)' },
        { value: 'manufacturing_date', label: 'Mfg Date' },
        { value: 'td',                 label: 'TD (HueForge)' },
        { value: 'message',            label: 'Custom Message' },
    ];

    var SOURCE_FIELDS = [
        { value: 'manufacturer',       label: 'manufacturer' },
        { value: 'type',               label: 'type' },
        { value: 'modifiers',          label: 'modifiers' },
        { value: 'colors',             label: 'colors' },
        { value: 'hotend_min_temp_c',  label: 'hotend_min_temp_c' },
        { value: 'hotend_max_temp_c',  label: 'hotend_max_temp_c' },
        { value: 'bed_temp_min_c',     label: 'bed_temp_min_c' },
        { value: 'bed_temp_max_c',     label: 'bed_temp_max_c' },
        { value: 'bed_temp_c',         label: 'bed_temp_c' },
        { value: 'diameter_mm',        label: 'diameter_mm' },
        { value: 'weight_grams',       label: 'weight_grams' },
        { value: 'drying_temp_c',      label: 'drying_temp_c' },
        { value: 'drying_time_hours',  label: 'drying_time_hours' },
        { value: 'manufacturing_date', label: 'manufacturing_date' },
        { value: 'td',                 label: 'td' },
        { value: 'emoji',              label: 'emoji' },
        { value: 'message',            label: 'message' },
    ];

    function buildSelect(options, selectedValue, className) {
        var sel = document.createElement('select');
        sel.className = 'mapping-select ' + className;
        options.forEach(function (opt) {
            var o = document.createElement('option');
            o.value = opt.value;
            o.textContent = opt.label;
            if (opt.value === selectedValue) o.selected = true;
            sel.appendChild(o);
        });
        return sel;
    }    function checkSpoolmanStatus(url, badge) {
        badge.textContent = '\u2026';
        badge.className = 'spoolman-status-badge spoolman-status-checking';
        fetch('/spools/api/spoolman-ping?url=' + encodeURIComponent(url))
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                if (data.reachable) {
                    badge.textContent = 'Connected \u2713';
                    badge.className = 'spoolman-status-badge spoolman-status-ok';
                } else {
                    badge.textContent = 'Not reachable';
                    badge.className = 'spoolman-status-badge spoolman-status-err';
                }
            })
            .catch(function () {
                badge.textContent = 'Check failed';
                badge.className = 'spoolman-status-badge spoolman-status-err';
            });
    }

    function findSpoolman(input, badge) {
        badge.textContent = 'Searching\u2026';
        badge.className = 'spoolman-status-badge spoolman-status-checking';
        fetch('/spools/api/spoolman-discover')
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                var candidates = data.candidates || [];
                if (candidates.length === 0) {
                    badge.textContent = 'Not found';
                    badge.className = 'spoolman-status-badge spoolman-status-err';
                    return;
                }
                if (candidates.length === 1) {
                    input.value = candidates[0];
                    checkSpoolmanStatus(candidates[0], badge);
                } else {
                    badge.textContent = '';
                    badge.className = 'spoolman-status-badge';
                    var wrap = input.parentElement;
                    var existing = wrap.querySelector('.spoolman-candidates');
                    if (existing) wrap.removeChild(existing);
                    var list = Templates.clone('spoolman-candidate-list');
                    candidates.forEach(function (c) {
                        var btn = Templates.clone('spoolman-candidate-btn');
                        btn.textContent = c;
                        btn.addEventListener('click', function () {
                            input.value = c;
                            wrap.removeChild(list);
                            checkSpoolmanStatus(c, badge);
                        });
                        list.appendChild(btn);
                    });
                    wrap.appendChild(list);
                }
            })
            .catch(function () {
                badge.textContent = 'Search failed';
                badge.className = 'spoolman-status-badge spoolman-status-err';
            });
    }

    function saveConfigPartial(payload, saveBtn, statusEl) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving\u2026';
        fetch('/spools/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (saved) {
                App.setConfig(saved);
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save';
                if (statusEl) {
                    statusEl.textContent = 'Saved';
                    statusEl.className = 'config-save-status config-save-ok';
                    setTimeout(function () {
                        statusEl.textContent = '';
                        statusEl.className = 'config-save-status';
                    }, 2000);
                }
            })
            .catch(function (err) {
                console.error('Config save failed:', err);
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save';
                if (statusEl) {
                    statusEl.textContent = 'Save failed';
                    statusEl.className = 'config-save-status config-save-err';
                }
            });
    }

    function buildPageShell(title) {
        var page = Templates.clone('config-page-shell');
        Templates.setText(page, '[data-id="heading"]', title);
        return page;
    }

    function buildSaveFooter(onSave) {
        var footer = Templates.clone('config-save-footer');
        var saveBtn = Templates.$(footer, '[data-id="save-btn"]');
        var statusEl = Templates.$(footer, '[data-id="status"]');
        saveBtn.addEventListener('click', function () { onSave(saveBtn, statusEl); });
        return footer;
    }

    return {
        DEFAULT_NAMES: DEFAULT_NAMES,
        GENERIC_FIELDS: GENERIC_FIELDS,
        SOURCE_FIELDS: SOURCE_FIELDS,
        buildSelect: buildSelect,
        checkSpoolmanStatus: checkSpoolmanStatus,
        findSpoolman: findSpoolman,
        saveConfigPartial: saveConfigPartial,
        buildPageShell: buildPageShell,
        buildSaveFooter: buildSaveFooter,
    };
})();
