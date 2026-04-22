'use strict';

// ── Spools page ─────────────────────────────────────────────────────────────
// Renders the 4-channel spool grid. Tag updates are pushed via SSE.

var SpoolsPage = (function () {

    var _sse = null;

    // Density defaults (g/cm³) by material type — mirrors backend MATERIAL_DENSITY table.
    var DENSITY_DEFAULTS = {
        'PLA': 1.24, 'PLA+': 1.24,
        'ABS': 1.05, 'ASA': 1.07,
        'PETG': 1.27, 'PET': 1.27,
        'TPU': 1.21, 'TPE': 1.21, 'FLEX': 1.21,
        'PA': 1.12, 'NYLON': 1.12,
        'PC': 1.20, 'HIPS': 1.05,
        'PVA': 1.23, 'PP': 0.91
    };

    function defaultDensity(material) {
        if (!material) return 1.24;
        var key = String(material).toUpperCase().split(/[\s\-\/]/)[0];
        return DENSITY_DEFAULTS[key] || 1.24;
    }

    function resolveFields(ch, config) {
        var mk = ch.moonraker || {};
        var tag = ch.tag || null;
        var filament = (tag && tag.filament) ? tag.filament : null;

        // Determine processor key
        var processorKey = 'generic';
        if (filament && filament.source_processor) {
            var proc = filament.source_processor;
            if (proc === 'tigertag_tag_processor') processorKey = 'tigertag';
            else if (proc === 'snapmaker_tag_processor') processorKey = 'snapmaker';
        } else if (mk.CARD_UID && Array.isArray(mk.CARD_UID)) {
            if (mk.CARD_UID.length === 4) processorKey = 'snapmaker';
        }

        var tagMappings = config && config.tag_mappings && config.tag_mappings[processorKey];

        // If mappings are configured, resolve each display field from the mapping
        // Otherwise fall through to the defaults below
        function mapped(toKey, defaultFn) {
            if (!tagMappings) return defaultFn();
            var rule = null;
            for (var i = 0; i < tagMappings.length; i++) {
                if (tagMappings[i].to === toKey) { rule = tagMappings[i]; break; }
            }
            if (!rule) return defaultFn();
            var src = rule.from;
            // Resolve from filament object if field exists there, otherwise from Moonraker mk
            if (filament && filament[src] !== undefined) return filament[src];
            if (mk[src] !== undefined) return mk[src];
            return defaultFn();
        }

        return {
            manufacturer:       mapped('manufacturer',       function () { return filament ? filament.manufacturer : (isMk(mk.VENDOR) ? mk.VENDOR : null); }),
            type:               mapped('type',               function () { return filament ? filament.type : (isMk(mk.MAIN_TYPE) ? mk.MAIN_TYPE : null); }),
            modifiers:          mapped('modifiers',          function () { return filament ? filament.modifiers : (isMk(mk.SUB_TYPE) ? [mk.SUB_TYPE] : []); }),
            colors:             mapped('color',              function () { return filament ? filament.colors : null; }),
            rgb1:               mk.RGB_1,
            hotend_min_temp_c:  mapped('hotend_min_temp',    function () { return filament ? filament.hotend_min_temp_c : mk.HOTEND_MIN_TEMP; }),
            hotend_max_temp_c:  mapped('hotend_max_temp',    function () { return filament ? filament.hotend_max_temp_c : mk.HOTEND_MAX_TEMP; }),
            bed_temp_c:         mapped('bed_temp_max',       function () { return filament ? filament.bed_temp_c : mk.BED_TEMP; }),
            bed_temp_min_c:     mapped('bed_temp_min',       function () { return filament ? filament.bed_temp_min_c : null; }),
            bed_temp_max_c:     mapped('bed_temp_max',       function () { return filament ? filament.bed_temp_max_c : null; }),
            first_layer_temp:   mk.FIRST_LAYER_TEMP,
            other_layer_temp:   mk.OTHER_LAYER_TEMP,
            diameter_mm:        mapped('diameter_mm',        function () { return filament ? filament.diameter_mm : mk.DIAMETER; }),
            weight_grams:       mapped('weight_grams',       function () { return filament ? filament.weight_grams : mk.WEIGHT; }),
            drying_temp_c:      mapped('drying_temp',        function () { return filament ? filament.drying_temp_c : mk.DRYING_TEMP; }),
            drying_time_hours:  mapped('drying_time',        function () { return filament ? filament.drying_time_hours : mk.DRYING_TIME; }),
            manufacturing_date: mapped('manufacturing_date', function () {
                return (filament && filament.manufacturing_date) ? filament.manufacturing_date : mk.MF_DATE;
            }),
            td:                 mapped('td',                 function () { return filament ? filament.td : null; }),
            message:            mapped('message',            function () {
                if (!filament) return null;
                var e = (filament.emoji || '').trim();
                var m = (filament.message || '').trim();
                return e && m ? e + ' ' + m : (m || e || null);
            }),
            uid:                (tag && tag.scan && tag.scan.uid) ? tag.scan.uid : mk.CARD_UID,
            processorKey:       processorKey,
        };
    }

    function renderChannel(ch, config) {
        var mk = ch.moonraker || {};
        var tag = ch.tag || null;
        var slotNames = (config && config.slot_names) || {};
        var slotNotes = (config && config.slot_notes) || {};
        var defaultNames = ['Slot 1 (Top-Left)', 'Slot 2 (Bottom-Left)', 'Slot 3 (Top-Right)', 'Slot 4 (Bottom-Right)'];

        var f = resolveFields(ch, config);

        var card = document.createElement('div');
        card.className = 'channel-card';

        // Header
        var header = document.createElement('div');
        header.className = 'channel-header';

        var label = document.createElement('div');
        label.className = 'channel-label-group';

        var nameEl = document.createElement('span');
        nameEl.className = 'channel-label';
        nameEl.textContent = slotNames[ch.channel] || slotNames[String(ch.channel)] || defaultNames[ch.channel] || ('Slot ' + (ch.channel + 1));
        label.appendChild(nameEl);

        var note = slotNotes[ch.channel] || slotNotes[String(ch.channel)] || '';
        if (note && note.trim()) {
            var noteEl = document.createElement('span');
            noteEl.className = 'channel-note';
            noteEl.textContent = note.trim();
            label.appendChild(noteEl);
        }

        header.appendChild(label);

        // Tag type badge
        var tagTypeName = null;
        if (tag && tag.filament && tag.filament.source_processor) {
            var proc = tag.filament.source_processor;
            if (proc === 'tigertag_tag_processor') tagTypeName = 'TigerTag';
            else if (proc === 'snapmaker_tag_processor') tagTypeName = 'Snapmaker';
            else if (proc === 'openspool_tag_processor') tagTypeName = 'OpenSpool';
            else tagTypeName = proc.replace(/_tag_processor$/, '');
        } else if (mk.CARD_UID && Array.isArray(mk.CARD_UID)) {
            if (mk.CARD_UID.length === 4) tagTypeName = 'Snapmaker';
            else if (mk.CARD_UID.length === 7) tagTypeName = 'TigerTag';
        }
        if (tagTypeName) {
            var badge = document.createElement('span');
            badge.className = 'tag-type-badge';
            badge.textContent = tagTypeName;
            header.appendChild(badge);
        }

        card.appendChild(header);

        // Body
        var body = document.createElement('div');
        body.className = 'channel-body';

        var hasData = isMk(mk.VENDOR) || isMk(mk.MAIN_TYPE) || (tag && tag.filament);

        if (!hasData) {
            var empty = document.createElement('div');
            empty.className = 'channel-empty';
            empty.textContent = 'No spool detected';
            body.appendChild(empty);
        } else {
            var fields = [];

            addField(fields, 'Vendor', f.manufacturer);
            addField(fields, 'Material', f.type);

            var mods = f.modifiers;
            if (mods && (Array.isArray(mods) ? mods.length > 0 : mods)) {
                addField(fields, 'Subtype', Array.isArray(mods) ? mods.join(', ') : mods);
            }

            // Color
            var colorHex = null;
            var colorSrc = f.colors;
            if (Array.isArray(colorSrc) && colorSrc.length > 0) {
                var argb = colorSrc[0];
                var r = (argb >> 16) & 0xFF;
                var g = (argb >> 8) & 0xFF;
                var b = argb & 0xFF;
                colorHex = '#' + ('0' + r.toString(16)).slice(-2) + ('0' + g.toString(16)).slice(-2) + ('0' + b.toString(16)).slice(-2);
            } else if (typeof colorSrc === 'number') {
                colorHex = colorToHex(colorSrc);
            } else if (typeof colorSrc === 'string' && colorSrc) {
                colorHex = colorSrc.startsWith('#') ? colorSrc : '#' + colorSrc;
            } else if (f.rgb1 !== undefined && f.rgb1 !== null && f.rgb1 !== 16777215) {
                colorHex = colorToHex(f.rgb1);
            }
            if (colorHex) {
                fields.push({ label: 'Color', value: createColorSwatch(colorHex), raw: true });
            }

            // Nozzle temps
            var minTemp = f.hotend_min_temp_c;
            var maxTemp = f.hotend_max_temp_c;
            if (minTemp || maxTemp) {
                fields.push({
                    label: 'Nozzle',
                    value: '<span class="temp-range">' + escapeHtml(minTemp || '?') + '–' + escapeHtml(maxTemp || '?') + ' °C</span>',
                    raw: true
                });
            }

            // Bed temps
            var bedMin = f.bed_temp_min_c;
            var bedMax = f.bed_temp_max_c;
            var bedTemp = f.bed_temp_c;
            if (bedMin && bedMax && bedMin > 0 && bedMax > 0 && bedMin !== bedMax) {
                fields.push({
                    label: 'Bed',
                    value: '<span class="temp-range">' + escapeHtml(Math.round(bedMin)) + '–' + escapeHtml(Math.round(bedMax)) + ' °C</span>',
                    raw: true
                });
            } else if (bedTemp && bedTemp > 0) {
                fields.push({
                    label: 'Bed',
                    value: '<span class="temp-range">' + escapeHtml(bedTemp) + ' °C</span>',
                    raw: true
                });
            }

            // First/other layer temps (Snapmaker raw fields)
            if (f.first_layer_temp && f.first_layer_temp > 0) {
                fields.push({ label: 'First Layer', value: '<span class="temp-range">' + escapeHtml(f.first_layer_temp) + ' °C</span>', raw: true });
            }
            if (f.other_layer_temp && f.other_layer_temp > 0) {
                fields.push({ label: 'Other Layers', value: '<span class="temp-range">' + escapeHtml(f.other_layer_temp) + ' °C</span>', raw: true });
            }

            if (f.diameter_mm && f.diameter_mm > 0) addField(fields, 'Diameter', f.diameter_mm + ' mm');
            if (f.weight_grams && f.weight_grams > 0) addField(fields, 'Weight', f.weight_grams + ' g');

            var dryTemp = f.drying_temp_c;
            var dryTime = f.drying_time_hours;
            if (dryTemp && dryTemp > 0) {
                var dryStr = dryTemp + ' °C';
                if (dryTime && dryTime > 0) dryStr += ' / ' + dryTime + ' h';
                fields.push({ label: 'Drying', value: '<span class="temp-range">' + escapeHtml(dryStr) + '</span>', raw: true });
            }

            var mfDate = f.manufacturing_date;
            if (mfDate && mfDate !== '19700101' && mfDate !== '0001-01-01' && mfDate !== 'NONE' && mfDate !== '') {
                if (typeof mfDate === 'string' && mfDate.length === 8) {
                    mfDate = mfDate.slice(0, 4) + '-' + mfDate.slice(4, 6) + '-' + mfDate.slice(6, 8);
                }
                addField(fields, 'Mfg Date', mfDate);
            }

            if (f.td && f.td > 0) addField(fields, 'TD', f.td + ' mm');

            if (f.message) addField(fields, 'Message', f.message);

            // UID
            var uid = f.uid;
            if (uid && uid !== 0) {
                var uidStr = Array.isArray(uid) ? formatUid(uid) : escapeHtml(uid);
                fields.push({ label: 'UID', value: '<span class="uid-value">' + uidStr + '</span>', raw: true });
            }

            // Render field grid
            var grid = document.createElement('div');
            grid.className = 'field-grid';
            for (var i = 0; i < fields.length; i++) {
                var fl = document.createElement('span');
                fl.className = 'field-label';
                fl.textContent = fields[i].label;
                var fv = document.createElement('span');
                fv.className = 'field-value';
                if (fields[i].raw) fv.innerHTML = fields[i].value;
                else fv.textContent = fields[i].value;
                grid.appendChild(fl);
                grid.appendChild(fv);
            }
            body.appendChild(grid);
        }

        card.appendChild(body);

        // Spoolman sync footer (shown when spoolman_url is configured and tag present)
        var spoolmanUrl = config && config.spoolman_url;
        if (spoolmanUrl && hasData && tag && tag.filament) {
            var spoolmanFooter = document.createElement('div');
            spoolmanFooter.className = 'channel-spoolman-footer';

            // Sync state badge (if already synced)
            var syncState = ch.spoolman_sync;
            if (syncState && syncState.filament_id) {
                var badgeRow = document.createElement('div');
                badgeRow.className = 'spoolman-sync-badge-row';
                var badge = document.createElement('a');
                badge.className = 'spoolman-sync-badge';
                badge.href = spoolmanUrl.replace(/\/$/, '') + '/filament/' + syncState.filament_id;
                badge.target = '_blank';
                badge.rel = 'noopener noreferrer';
                var badgeParts = ['Synced \u2713 \u00b7 Filament #' + syncState.filament_id];
                if (syncState.spool_id) badgeParts.push('Spool #' + syncState.spool_id);
                badge.textContent = badgeParts.join(' \u00b7 ');
                badgeRow.appendChild(badge);
                spoolmanFooter.appendChild(badgeRow);
            }

            // Name row (full width)
            var nameRow = document.createElement('div');
            nameRow.className = 'spoolman-name-row';
            var nameInput = document.createElement('input');
            nameInput.type = 'text';
            nameInput.className = 'spoolman-name-input';
            nameInput.placeholder = 'Filament name';
            // Smart pre-fill: TigerTag uses message, others use type + manufacturer
            if (f.message) {
                nameInput.value = f.message;
            } else {
                var nameParts = [f.type, f.manufacturer].filter(Boolean);
                if (nameParts.length) nameInput.value = nameParts.join(' ');
            }
            nameRow.appendChild(nameInput);

            // Density + sync row
            var densityRow = document.createElement('div');
            densityRow.className = 'spoolman-density-row';
            var densityLabel = document.createElement('span');
            densityLabel.className = 'spoolman-density-label';
            densityLabel.textContent = 'Density';
            var densityInput = document.createElement('input');
            densityInput.type = 'number';
            densityInput.className = 'spoolman-density-input';
            densityInput.step = '0.01';
            densityInput.min = '0.1';
            densityInput.max = '3.0';
            densityInput.value = defaultDensity(f.type);
            var densityUnit = document.createElement('span');
            densityUnit.className = 'spoolman-density-unit';
            densityUnit.textContent = 'g/cm\u00b3';
            var syncBtn = document.createElement('button');
            syncBtn.className = 'spoolman-sync-btn';
            syncBtn.textContent = 'Sync \u2197';
            densityRow.appendChild(densityLabel);
            densityRow.appendChild(densityInput);
            densityRow.appendChild(densityUnit);
            densityRow.appendChild(syncBtn);

            var syncStatus = document.createElement('div');
            syncStatus.className = 'spoolman-sync-status';

            var channelIndex = ch.channel;

            // Link-to-existing row (secondary)
            var linkRow = document.createElement('div');
            linkRow.className = 'spoolman-link-row';

            var findBtn = document.createElement('button');
            findBtn.className = 'spoolman-find-btn';
            findBtn.textContent = '\u21c4 Find existing';

            var linkSelect = document.createElement('select');
            linkSelect.className = 'spoolman-link-select';
            var defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.textContent = '\u2014 Create new spool \u2014';
            linkSelect.appendChild(defaultOpt);

            findBtn.addEventListener('click', function () {
                findExistingFilaments(channelIndex, linkSelect, findBtn);
            });

            linkRow.appendChild(findBtn);
            linkRow.appendChild(linkSelect);

            syncBtn.addEventListener('click', function () {
                var filamentId = linkSelect.value || null;
                syncToSpoolman(channelIndex, nameInput, densityInput, syncStatus, syncBtn, filamentId);
            });

            spoolmanFooter.appendChild(nameRow);
            spoolmanFooter.appendChild(densityRow);
            spoolmanFooter.appendChild(linkRow);
            spoolmanFooter.appendChild(syncStatus);
            card.appendChild(spoolmanFooter);
        } else if (!spoolmanUrl && hasData && tag && tag.filament) {
            // Onboarding: no Spoolman configured yet
            var onboardFooter = document.createElement('div');
            onboardFooter.className = 'channel-spoolman-footer channel-spoolman-onboard';
            var onboardLink = document.createElement('a');
            onboardLink.href = '#config';
            onboardLink.className = 'spoolman-onboard-link';
            onboardLink.textContent = 'Connect Spoolman to sync \u2192';
            onboardLink.addEventListener('click', function (e) {
                e.preventDefault();
                App.navigate('config');
            });
            onboardFooter.appendChild(onboardLink);
            card.appendChild(onboardFooter);
        }

        return card;
    }

    function syncToSpoolman(channel, nameInput, densityInput, statusEl, btn, filamentId) {
        btn.disabled = true;
        btn.textContent = 'Syncing\u2026';
        statusEl.textContent = '';
        statusEl.className = 'spoolman-sync-status';
        var density = parseFloat(densityInput.value);
        var body = { name: nameInput.value.trim(), density: isNaN(density) ? 1.24 : density };
        if (filamentId) body.filament_id = filamentId;
        fetch('/spools/api/spoolman-sync?channel=' + channel, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        })
            .then(function (resp) {
                if (!resp.ok) return resp.json().then(function (e) {
                    var msg = e.error || ('HTTP ' + resp.status);
                    if (resp.status === 502) {
                        msg = 'Cannot reach Spoolman \u2014 check the URL in Config';
                    } else if (resp.status === 400 && (msg.indexOf('uid') !== -1 || msg.indexOf('UID') !== -1)) {
                        msg = 'Tag has no UID \u2014 cannot link to Spoolman';
                    }
                    // For all other errors (including 422) show the actual detail
                    throw new Error(msg);
                });
                return resp.json();
            })
            .then(function (data) {
                btn.disabled = false;
                btn.textContent = 'Sync \u2197';
                statusEl.textContent = data.created_filament ? 'Created \u2713' : 'Updated \u2713';
                statusEl.className = 'spoolman-sync-status spoolman-sync-ok';
                // Refresh the card to update the sync badge
                fetchChannels();
            })
            .catch(function (err) {
                btn.disabled = false;
                btn.textContent = 'Sync \u2197';
                statusEl.textContent = err.message;
                statusEl.className = 'spoolman-sync-status spoolman-sync-err';
            });
    }

    function findExistingFilaments(channel, linkSelect, btn) {
        btn.disabled = true;
        btn.textContent = 'Searching\u2026';
        fetch('/spools/api/spoolman-candidates?channel=' + channel)
            .then(function (resp) { return resp.json(); })
            .then(function (data) {
                btn.disabled = false;
                btn.textContent = '\u21c4 Find existing';
                // Remove all non-default options
                while (linkSelect.options.length > 1) linkSelect.remove(1);
                var candidates = data.candidates || [];
                if (candidates.length === 0) {
                    var noMatch = document.createElement('option');
                    noMatch.disabled = true;
                    noMatch.textContent = '(no matches in Spoolman)';
                    linkSelect.appendChild(noMatch);
                } else {
                    candidates.forEach(function (c) {
                        var opt = document.createElement('option');
                        opt.value = c.id;
                        var parts = [c.vendor_name, c.material, c.name].filter(Boolean);
                        var label = parts.join(' \u00b7 ');
                        if (c.color_hex) label += ' #' + c.color_hex;
                        if (c.external_id) label += ' [linked]';
                        label += ' [ID:' + c.id + ']';
                        opt.textContent = label;
                        linkSelect.appendChild(opt);
                    });
                }
            })
            .catch(function (err) {
                btn.disabled = false;
                btn.textContent = '\u21c4 Find existing';
                console.error('Candidates fetch failed:', err);
            });
    }

    function startSSE() {
        if (_sse) return;
        _sse = new EventSource('/spools/api/events');
        _sse.addEventListener('tag-event', function () { fetchChannels(); });
        _sse.addEventListener('tag-removed', function () { fetchChannels(); });
        _sse.onerror = function () {
            _sse.close();
            _sse = null;
            App.setConnectionStatus(false);
            // Retry after 5s
            setTimeout(startSSE, 5000);
        };
    }

    function mount(container) {
        var section = document.createElement('section');
        section.id = 'channels';
        section.className = 'channels-grid';
        container.appendChild(section);
        fetchChannels();
        startSSE();
    }

    function unmount() {
        if (_sse) {
            _sse.close();
            _sse = null;
        }
    }

    function fetchChannels() {
        var config = App.getConfig();
        fetch('/spools/api/channels')
            .then(function (resp) {
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                return resp.json();
            })
            .then(function (data) {
                App.setConnectionStatus(true);
                var container = document.getElementById('channels');
                if (!container) return;
                container.innerHTML = '';
                var channels = data.channels || [];
                for (var i = 0; i < channels.length; i++) {
                    container.appendChild(renderChannel(channels[i], config));
                }
            })
            .catch(function (err) {
                App.setConnectionStatus(false);
                console.error('Failed to fetch channels:', err);
            });
    }

    return { mount: mount, unmount: unmount, fetchChannels: fetchChannels };
})();

function scanAll() {
    var btn = document.getElementById('scan-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Scanning\u2026'; }
    fetch('/spools/api/scan', { method: 'POST' })
        .then(function (resp) { return resp.json(); })
        .then(function () {
            // SSE will pick up the tag event; just re-enable the button
            if (btn) { btn.disabled = false; btn.textContent = 'Scan All'; }
        })
        .catch(function (err) {
            console.error('Scan failed:', err);
            if (btn) { btn.disabled = false; btn.textContent = 'Scan All'; }
        });
}
