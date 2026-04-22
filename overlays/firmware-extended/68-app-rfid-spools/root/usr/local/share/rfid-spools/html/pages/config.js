'use strict';

// ── Config page ──────────────────────────────────────────────────────────────
// Slot name overrides, per-slot notes, and tag field mappings.

var ConfigPage = (function () {

    var DEFAULT_NAMES = [
        'Slot 1 (Top-Left)',
        'Slot 2 (Bottom-Left)',
        'Slot 3 (Top-Right)',
        'Slot 4 (Bottom-Right)'
    ];

    // Display-model destination fields shown in the left dropdown
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

    // Source fields per processor type (right dropdown)
    var SOURCE_FIELDS = {
        tigertag: [
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
        ],
        snapmaker: [
            { value: 'VENDOR',           label: 'VENDOR' },
            { value: 'MAIN_TYPE',        label: 'MAIN_TYPE' },
            { value: 'SUB_TYPE',         label: 'SUB_TYPE' },
            { value: 'RGB_1',            label: 'RGB_1' },
            { value: 'HOTEND_MIN_TEMP',  label: 'HOTEND_MIN_TEMP' },
            { value: 'HOTEND_MAX_TEMP',  label: 'HOTEND_MAX_TEMP' },
            { value: 'BED_TEMP',         label: 'BED_TEMP' },
            { value: 'FIRST_LAYER_TEMP', label: 'FIRST_LAYER_TEMP' },
            { value: 'OTHER_LAYER_TEMP', label: 'OTHER_LAYER_TEMP' },
            { value: 'DIAMETER',         label: 'DIAMETER' },
            { value: 'WEIGHT',           label: 'WEIGHT' },
            { value: 'DRYING_TEMP',      label: 'DRYING_TEMP' },
            { value: 'DRYING_TIME',      label: 'DRYING_TIME' },
            { value: 'MF_DATE',          label: 'MF_DATE' },
        ],
        generic: [
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
        ],
    };

    var PROCESSOR_LABELS = {
        tigertag: 'TigerTag',
        snapmaker: 'Snapmaker',
        generic: 'Generic / Other',
    };

    function mount(container) {
        var config = App.getConfig();
        var slotNames = config.slot_names || {};
        var slotNotes = config.slot_notes || {};

        var page = document.createElement('div');
        page.className = 'config-page';

        var heading = document.createElement('h2');
        heading.className = 'config-heading';
        heading.textContent = 'Configuration';
        page.appendChild(heading);

        // ── Slot settings ──────────────────────────────────────────────────
        var section = document.createElement('div');
        section.className = 'config-section';

        var sectionTitle = document.createElement('h3');
        sectionTitle.className = 'config-section-title';
        sectionTitle.textContent = 'Slot Settings';
        section.appendChild(sectionTitle);

        for (var i = 0; i < 4; i++) {
            section.appendChild(buildSlotRow(i, slotNames, slotNotes));
        }
        page.appendChild(section);

        // ── Tag Mappings ───────────────────────────────────────────────────
        var tagMappings = config.tag_mappings || {};
        var mappingSection = document.createElement('div');
        mappingSection.className = 'config-section';

        var mappingTitle = document.createElement('h3');
        mappingTitle.className = 'config-section-title';
        mappingTitle.textContent = 'Tag Field Mappings';
        mappingSection.appendChild(mappingTitle);

        var processorKeys = ['tigertag', 'snapmaker', 'generic'];
        processorKeys.forEach(function (key) {
            mappingSection.appendChild(buildMappingBlock(key, tagMappings[key] || []));
        });
        page.appendChild(mappingSection);

        // ── Spoolman Integration ───────────────────────────────────────────
        page.appendChild(buildSpoolmanSection(config));

        // ── Save button ────────────────────────────────────────────────────
        var footer = document.createElement('div');
        footer.className = 'config-footer';

        var saveBtn = document.createElement('button');
        saveBtn.className = 'config-save-btn';
        saveBtn.textContent = 'Save';
        saveBtn.addEventListener('click', function () { saveConfig(page, saveBtn); });
        footer.appendChild(saveBtn);

        var status = document.createElement('span');
        status.id = 'config-save-status';
        status.className = 'config-save-status';
        footer.appendChild(status);

        page.appendChild(footer);
        container.appendChild(page);
    }

    function unmount() {}

    function buildSlotRow(index, slotNames, slotNotes) {
        var row = document.createElement('div');
        row.className = 'config-slot-row';
        row.dataset.slot = index;

        var slotLabel = document.createElement('div');
        slotLabel.className = 'config-slot-label';
        slotLabel.textContent = DEFAULT_NAMES[index];
        row.appendChild(slotLabel);

        var fields = document.createElement('div');
        fields.className = 'config-slot-fields';

        // Name override
        var nameLabel = document.createElement('label');
        nameLabel.className = 'config-field-label';
        nameLabel.textContent = 'Custom name';
        var nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.className = 'config-input';
        nameInput.placeholder = DEFAULT_NAMES[index];
        nameInput.value = slotNames[index] || slotNames[String(index)] || '';
        nameInput.dataset.configKey = 'slot_names';
        nameInput.dataset.slot = index;
        nameLabel.appendChild(nameInput);
        fields.appendChild(nameLabel);

        // Note
        var noteLabel = document.createElement('label');
        noteLabel.className = 'config-field-label';
        noteLabel.textContent = 'Note';
        var noteInput = document.createElement('textarea');
        noteInput.className = 'config-textarea';
        noteInput.placeholder = 'e.g. backup spool, low remaining…';
        noteInput.rows = 2;
        noteInput.value = slotNotes[index] || slotNotes[String(index)] || '';
        noteInput.dataset.configKey = 'slot_notes';
        noteInput.dataset.slot = index;
        noteLabel.appendChild(noteInput);
        fields.appendChild(noteLabel);

        row.appendChild(fields);
        return row;
    }

    function saveConfig(page, saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = 'Saving…';

        var slotNames = {};
        var slotNotes = {};

        var nameInputs = page.querySelectorAll('input[data-config-key="slot_names"]');
        nameInputs.forEach(function (inp) {
            slotNames[inp.dataset.slot] = inp.value.trim();
        });

        var noteInputs = page.querySelectorAll('textarea[data-config-key="slot_notes"]');
        noteInputs.forEach(function (inp) {
            slotNotes[inp.dataset.slot] = inp.value.trim();
        });

        var spoolmanInput = page.querySelector('#spoolman-url-input');
        var spoolmanUrl = spoolmanInput ? spoolmanInput.value.trim() : '';
        var extraCbs = page.querySelectorAll('input[data-extra-key]');
        var spoolmanExtraFields = {};
        extraCbs.forEach(function (cb) { spoolmanExtraFields[cb.dataset.extraKey] = cb.checked; });
        var payload = { slot_names: slotNames, slot_notes: slotNotes, tag_mappings: collectTagMappings(page), spoolman_url: spoolmanUrl, spoolman_extra_fields: spoolmanExtraFields };

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
                var status = document.getElementById('config-save-status');
                if (status) {
                    status.textContent = 'Saved';
                    status.className = 'config-save-status config-save-ok';
                    setTimeout(function () { status.textContent = ''; status.className = 'config-save-status'; }, 2000);
                }
            })
            .catch(function (err) {
                console.error('Config save failed:', err);
                saveBtn.disabled = false;
                saveBtn.textContent = 'Save';
                var status = document.getElementById('config-save-status');
                if (status) {
                    status.textContent = 'Save failed';
                    status.className = 'config-save-status config-save-err';
                }
            });
    }

    function collectTagMappings(page) {
        var result = {};
        var blocks = page.querySelectorAll('.mapping-block');
        blocks.forEach(function (block) {
            var key = block.dataset.processor;
            var rows = [];
            block.querySelectorAll('.mapping-row').forEach(function (row) {
                var toSel = row.querySelector('.mapping-to');
                var fromSel = row.querySelector('.mapping-from');
                if (toSel && fromSel && toSel.value && fromSel.value) {
                    rows.push({ to: toSel.value, from: fromSel.value });
                }
            });
            result[key] = rows;
        });
        return result;
    }

    function buildMappingBlock(processorKey, mappingRows) {
        var srcFields = SOURCE_FIELDS[processorKey] || SOURCE_FIELDS.generic;

        var block = document.createElement('div');
        block.className = 'mapping-block';
        block.dataset.processor = processorKey;

        var label = document.createElement('div');
        label.className = 'mapping-processor-label';
        label.textContent = PROCESSOR_LABELS[processorKey] || processorKey;
        block.appendChild(label);

        var table = document.createElement('div');
        table.className = 'mapping-table';
        block.appendChild(table);

        function addRow(toVal, fromVal) {
            var row = document.createElement('div');
            row.className = 'mapping-row';

            var toSel = buildSelect(GENERIC_FIELDS, toVal, 'mapping-to');
            var arrow = document.createElement('span');
            arrow.className = 'mapping-arrow';
            arrow.textContent = '\u2190';
            var fromSel = buildSelect(srcFields, fromVal, 'mapping-from');

            var removeBtn = document.createElement('button');
            removeBtn.className = 'mapping-remove-btn';
            removeBtn.textContent = '\u00d7';
            removeBtn.title = 'Remove row';
            removeBtn.addEventListener('click', function () { table.removeChild(row); });

            row.appendChild(toSel);
            row.appendChild(arrow);
            row.appendChild(fromSel);
            row.appendChild(removeBtn);
            table.appendChild(row);
        }

        mappingRows.forEach(function (r) { addRow(r.to, r.from); });

        var addBtn = document.createElement('button');
        addBtn.className = 'mapping-add-btn';
        addBtn.textContent = '+ Add row';
        addBtn.addEventListener('click', function () {
            addRow(GENERIC_FIELDS[0].value, srcFields[0].value);
        });
        block.appendChild(addBtn);

        return block;
    }

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
    }

    function buildSpoolmanSection(config) {
        var section = document.createElement('div');
        section.className = 'config-section';

        var title = document.createElement('h3');
        title.className = 'config-section-title';
        title.textContent = 'Spoolman Integration';
        section.appendChild(title);

        var row = document.createElement('div');
        row.className = 'config-slot-row';

        var label = document.createElement('label');
        label.className = 'config-field-label';
        label.textContent = 'Server URL';

        var inputWrap = document.createElement('div');
        inputWrap.className = 'config-spoolman-input-wrap';

        var input = document.createElement('input');
        input.type = 'text';
        input.id = 'spoolman-url-input';
        input.className = 'config-input';
        input.placeholder = 'http://spoolman.local:7912';
        input.value = (config && config.spoolman_url) || '';

        var badge = document.createElement('span');
        badge.className = 'spoolman-status-badge';

        input.addEventListener('change', function () {
            var url = input.value.trim();
            if (url) checkSpoolmanStatus(url, badge);
            else { badge.textContent = ''; badge.className = 'spoolman-status-badge'; }
        });

        inputWrap.appendChild(input);
        inputWrap.appendChild(badge);
        label.appendChild(inputWrap);
        row.appendChild(label);
        section.appendChild(row);

        var btnRow = document.createElement('div');
        btnRow.className = 'config-spoolman-btn-row';

        var findBtn = document.createElement('button');
        findBtn.className = 'config-btn-secondary';
        findBtn.textContent = 'Find Spoolman';
        findBtn.addEventListener('click', function () { findSpoolman(input, badge); });
        btnRow.appendChild(findBtn);
        section.appendChild(btnRow);

        // Per-field extra fields table
        var EXTRA_FIELDS = [
            { key: 'max_extruder_temp', label: 'Max extruder temp',    hint: 'hotend_max_temp_c' },
            { key: 'max_bed_temp',      label: 'Max bed temp',          hint: 'bed_temp_max_c' },
            { key: 'drying_temp',       label: 'Drying temperature',    hint: 'drying_temp_c' },
            { key: 'drying_time',       label: 'Drying time (h)',        hint: 'drying_time_hours' },
            { key: 'td',                label: 'Transmission distance', hint: 'td' },
            { key: 'mfg_date',          label: 'Manufacturing date',     hint: 'manufacturing_date' },
            { key: 'modifiers',         label: 'Modifiers / finish',     hint: 'modifiers' },
        ];
        var extraFields = (config && config.spoolman_extra_fields) || {};

        var extraTitle = document.createElement('div');
        extraTitle.className = 'config-extra-fields-title';
        extraTitle.textContent = 'Extra fields to sync (requires custom fields in Spoolman)';
        section.appendChild(extraTitle);

        var table = document.createElement('div');
        table.className = 'config-extra-fields-table';
        function refreshFieldStatus() {
            var url = input.value.trim();
            if (!url) return;
            fetch('/spools/api/spoolman-extra-fields-status')
                .then(function (resp) { return resp.json(); })
                .then(function (data) {
                    if (!data.fields) return;
                    EXTRA_FIELDS.forEach(function (f) {
                        var row = table.querySelector('[data-extra-field-row="' + f.key + '"]');
                        if (!row) return;
                        var sb = row.querySelector('.config-extra-field-status');
                        if (!sb) return;
                        if (data.fields[f.key] === true) {
                            sb.textContent = '\u2713';
                            sb.className = 'config-extra-field-status config-extra-field-status-ok';
                        } else {
                            sb.textContent = '\u2717';
                            sb.className = 'config-extra-field-status config-extra-field-status-missing';
                        }
                    });
                })
                .catch(function () {});
        }

        EXTRA_FIELDS.forEach(function (f) {
            var row = document.createElement('label');
            row.className = 'config-extra-field-row';
            row.dataset.extraFieldRow = f.key;

            var cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.dataset.extraKey = f.key;
            cb.className = 'config-extra-field-cb';
            cb.checked = !!(extraFields[f.key]);

            var labelText = document.createElement('span');
            labelText.className = 'config-extra-field-label';
            labelText.textContent = f.label;

            var keyBadge = document.createElement('code');
            keyBadge.className = 'config-extra-field-key';
            keyBadge.textContent = f.key;

            var statusBadge = document.createElement('span');
            statusBadge.className = 'config-extra-field-status';
            statusBadge.textContent = '\u2026';

            row.appendChild(cb);
            row.appendChild(labelText);
            row.appendChild(keyBadge);
            row.appendChild(statusBadge);
            table.appendChild(row);
        });
        section.appendChild(table);

        // Register fields button
        var regRow = document.createElement('div');
        regRow.className = 'config-spoolman-syncall-row';
        var regBtn = document.createElement('button');
        regBtn.className = 'config-btn-secondary';
        regBtn.textContent = 'Register fields in Spoolman';
        var regStatus = document.createElement('span');
        regStatus.className = 'spoolman-status-badge';
        regBtn.addEventListener('click', function () {
            regBtn.disabled = true;
            regStatus.textContent = 'Registering\u2026';
            regStatus.className = 'spoolman-status-badge spoolman-status-checking';
            fetch('/spools/api/spoolman-register-extra-fields', { method: 'POST' })
                .then(function (resp) { return resp.json(); })
                .then(function (data) {
                    regBtn.disabled = false;
                    var newCount = (data.registered || []).length;
                    var existCount = (data.already_existed || []).length;
                    var errKeys = Object.keys(data.errors || {});
                    var okTotal = newCount + existCount;
                    if (errKeys.length > 0) {
                        var errDetails = errKeys.map(function (k) { return k + ': ' + (data.errors[k] || '?'); }).join('; ');
                        regStatus.textContent = okTotal + ' ok, ' + errKeys.length + ' failed \u2014 ' + errDetails;
                        regStatus.className = 'spoolman-status-badge spoolman-status-err';
                    } else {
                        regStatus.textContent = okTotal + ' field(s) ready \u2713';
                        regStatus.className = 'spoolman-status-badge spoolman-status-ok';
                    }
                    refreshFieldStatus();
                })
                .catch(function (err) {
                    regBtn.disabled = false;
                    regStatus.textContent = err.message;
                    regStatus.className = 'spoolman-status-badge spoolman-status-err';
                });
        });
        regRow.appendChild(regBtn);
        regRow.appendChild(regStatus);
        section.appendChild(regRow);

        if (input.value) { checkSpoolmanStatus(input.value.trim(), badge); refreshFieldStatus(); }

        return section;
    }

    function checkSpoolmanStatus(url, badge) {
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
                    var list = document.createElement('div');
                    list.className = 'spoolman-candidates';
                    candidates.forEach(function (c) {
                        var btn = document.createElement('button');
                        btn.className = 'spoolman-candidate-btn';
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

    return { mount: mount, unmount: unmount };
})();
