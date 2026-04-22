'use strict';

// ── Spoolman config page ─────────────────────────────────────────────────────

var SpoolmanConfigPage = (function () {

    var EXTRA_FIELDS = [
        { key: 'max_extruder_temp', label: 'Max extruder temp',    hint: 'hotend_max_temp_c' },
        { key: 'max_bed_temp',      label: 'Max bed temp',          hint: 'bed_temp_max_c' },
        { key: 'drying_temp',       label: 'Drying temperature',    hint: 'drying_temp_c' },
        { key: 'drying_time',       label: 'Drying time (h)',        hint: 'drying_time_hours' },
        { key: 'td',                label: 'Transmission distance', hint: 'td' },
        { key: 'mfg_date',          label: 'Manufacturing date',     hint: 'manufacturing_date' },
        { key: 'modifiers',         label: 'Modifiers / finish',     hint: 'modifiers' },
    ];

    function mount(container) {
        var config = App.getConfig();
        var page = ConfigShared.buildPageShell('Spoolman');

        var section = document.createElement('div');
        section.className = 'config-section';

        // URL row
        var urlRow = document.createElement('div');
        urlRow.className = 'config-slot-row';
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
            if (url) ConfigShared.checkSpoolmanStatus(url, badge);
            else { badge.textContent = ''; badge.className = 'spoolman-status-badge'; }
        });

        inputWrap.appendChild(input);
        inputWrap.appendChild(badge);
        label.appendChild(inputWrap);
        urlRow.appendChild(label);
        section.appendChild(urlRow);

        var btnRow = document.createElement('div');
        btnRow.className = 'config-spoolman-btn-row';
        var findBtn = document.createElement('button');
        findBtn.className = 'config-btn-secondary';
        findBtn.textContent = 'Find Spoolman';
        findBtn.addEventListener('click', function () { ConfigShared.findSpoolman(input, badge); });
        btnRow.appendChild(findBtn);
        section.appendChild(btnRow);

        // Extra fields table
        var extraFields = (config && config.spoolman_extra_fields) || {};

        var extraTitle = document.createElement('div');
        extraTitle.className = 'config-extra-fields-title';
        extraTitle.textContent = 'Extra fields to sync (requires custom fields in Spoolman)';
        section.appendChild(extraTitle);

        var table = document.createElement('div');
        table.className = 'config-extra-fields-table';

        function refreshFieldStatus() {
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
                        var errDetails = errKeys.map(function (k) {
                            return k + ': ' + (data.errors[k] || '?');
                        }).join('; ');
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

        page.appendChild(section);

        page.appendChild(ConfigShared.buildSaveFooter(function (saveBtn, statusEl) {
            var extraCbs = page.querySelectorAll('input[data-extra-key]');
            var spoolmanExtraFields = {};
            extraCbs.forEach(function (cb) { spoolmanExtraFields[cb.dataset.extraKey] = cb.checked; });
            ConfigShared.saveConfigPartial(
                { spoolman_url: input.value.trim(), spoolman_extra_fields: spoolmanExtraFields },
                saveBtn, statusEl
            );
        }));

        if (input.value) {
            ConfigShared.checkSpoolmanStatus(input.value.trim(), badge);
            refreshFieldStatus();
        }

        container.appendChild(page);
    }

    function unmount() {}

    return { mount: mount, unmount: unmount };
})();
