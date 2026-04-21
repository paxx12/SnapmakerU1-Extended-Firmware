'use strict';

const CHANNEL_NAMES = ['Slot 1 (Top-Left)', 'Slot 2 (Bottom-Left)', 'Slot 3 (Top-Right)', 'Slot 4 (Bottom-Right)'];
const POLL_INTERVAL = 3000;

let pollTimer = null;

function setConnectionStatus(connected) {
    const dot = document.getElementById('connection-status');
    const text = document.getElementById('connection-text');
    dot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
    text.textContent = connected ? 'Connected' : 'Disconnected';
}

function formatUid(uidArray) {
    if (!uidArray || !Array.isArray(uidArray)) return '—';
    return uidArray.map(function (b) { return ('0' + b.toString(16)).slice(-2).toUpperCase(); }).join(':');
}

function colorToHex(rgb, alpha) {
    if (rgb === undefined || rgb === null) return null;
    var r = (rgb >> 16) & 0xFF;
    var g = (rgb >> 8) & 0xFF;
    var b = rgb & 0xFF;
    return '#' + ('0' + r.toString(16)).slice(-2) + ('0' + g.toString(16)).slice(-2) + ('0' + b.toString(16)).slice(-2);
}

function createColorSwatch(hexColor) {
    if (!hexColor) return '';
    return '<span class="color-swatch" style="background:' + escapeAttr(hexColor) + '"></span>' + escapeHtml(hexColor);
}

function escapeHtml(str) {
    if (str === null || str === undefined) return '—';
    var s = String(str);
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeAttr(str) {
    return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function isMk(val) {
    // Moonraker uses 'NONE' as empty sentinel — treat it as missing
    return val !== undefined && val !== null && val !== '' && val !== 'NONE';
}

function addField(fields, label, value) {
    if (value === undefined || value === null || value === '' || value === 0 || value === 'NONE') return;
    fields.push({ label: label, value: value });
}

function renderChannel(ch) {
    var mk = ch.moonraker || {};
    var tag = ch.tag || null;

    var card = document.createElement('div');
    card.className = 'channel-card';

    // Header
    var header = document.createElement('div');
    header.className = 'channel-header';

    var label = document.createElement('span');
    label.className = 'channel-label';
    label.textContent = CHANNEL_NAMES[ch.channel] || ('Slot ' + (ch.channel + 1));

    header.appendChild(label);

    // Tag type badge — prefer webhook source, fall back to UID-length heuristic
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

        // Prefer tag data when available, fall back to Moonraker
        var filament = (tag && tag.filament) ? tag.filament : null;

        addField(fields, 'Vendor', filament ? filament.manufacturer : (isMk(mk.VENDOR) ? mk.VENDOR : null));
        addField(fields, 'Material', filament ? filament.type : (isMk(mk.MAIN_TYPE) ? mk.MAIN_TYPE : null));

        if (filament && filament.modifiers && filament.modifiers.length > 0) {
            addField(fields, 'Subtype', filament.modifiers.join(', '));
        } else if (isMk(mk.SUB_TYPE)) {
            addField(fields, 'Subtype', mk.SUB_TYPE);
        }

        // Color
        var colorHex = null;
        if (filament && filament.colors && filament.colors.length > 0) {
            // ARGB format from OpenRFID
            var argb = filament.colors[0];
            var r = (argb >> 16) & 0xFF;
            var g = (argb >> 8) & 0xFF;
            var b = argb & 0xFF;
            colorHex = '#' + ('0' + r.toString(16)).slice(-2) + ('0' + g.toString(16)).slice(-2) + ('0' + b.toString(16)).slice(-2);
        } else if (mk.RGB_1 !== undefined && mk.RGB_1 !== null && mk.RGB_1 !== 16777215) {
            // 16777215 = 0xFFFFFF = white default/empty sentinel from Moonraker
            colorHex = colorToHex(mk.RGB_1);
        }
        if (colorHex) {
            fields.push({ label: 'Color', value: createColorSwatch(colorHex), raw: true });
        }

        // Temps
        var minTemp = filament ? filament.hotend_min_temp_c : mk.HOTEND_MIN_TEMP;
        var maxTemp = filament ? filament.hotend_max_temp_c : mk.HOTEND_MAX_TEMP;
        if (minTemp || maxTemp) {
            fields.push({
                label: 'Nozzle',
                value: '<span class="temp-range">' + escapeHtml(minTemp || '?') + '–' + escapeHtml(maxTemp || '?') + ' °C</span>',
                raw: true
            });
        }

        var bedTemp = filament ? filament.bed_temp_c : mk.BED_TEMP;
        var bedMin = filament ? filament.bed_temp_min_c : null;
        var bedMax = filament ? filament.bed_temp_max_c : null;
        if ((bedMin && bedMax && bedMin > 0 && bedMax > 0) && bedMin !== bedMax) {
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

        // First layer / other layer temps
        var firstLayerTemp = mk.FIRST_LAYER_TEMP;
        var otherLayerTemp = mk.OTHER_LAYER_TEMP;
        if (firstLayerTemp && firstLayerTemp > 0) {
            fields.push({ label: 'First Layer', value: '<span class="temp-range">' + escapeHtml(firstLayerTemp) + ' °C</span>', raw: true });
        }
        if (otherLayerTemp && otherLayerTemp > 0) {
            fields.push({ label: 'Other Layers', value: '<span class="temp-range">' + escapeHtml(otherLayerTemp) + ' °C</span>', raw: true });
        }

        // Diameter
        var diameter = filament ? filament.diameter_mm : mk.DIAMETER;
        if (diameter && diameter > 0) {
            addField(fields, 'Diameter', diameter + ' mm');
        }

        // Weight
        var weight = filament ? filament.weight_grams : mk.WEIGHT;
        if (weight && weight > 0) {
            addField(fields, 'Weight', weight + ' g');
        }

        // Drying conditions
        var dryTemp = filament ? filament.drying_temp_c : mk.DRYING_TEMP;
        var dryTime = filament ? filament.drying_time_hours : mk.DRYING_TIME;
        if (dryTemp && dryTemp > 0) {
            var dryStr = dryTemp + ' °C';
            if (dryTime && dryTime > 0) dryStr += ' / ' + dryTime + ' h';
            fields.push({ label: 'Drying', value: '<span class="temp-range">' + escapeHtml(dryStr) + '</span>', raw: true });
        }

        // Manufacturing date — prefer webhook filament field, fall back to Moonraker MF_DATE
        var mfDate = (filament && filament.manufacturing_date) ? filament.manufacturing_date : mk.MF_DATE;
        if (mfDate && mfDate !== '19700101' && mfDate !== '0001-01-01' && mfDate !== 'NONE' && mfDate !== '') {
            if (mfDate.length === 8) {
                mfDate = mfDate.slice(0, 4) + '-' + mfDate.slice(4, 6) + '-' + mfDate.slice(6, 8);
            }
            addField(fields, 'Mfg Date', mfDate);
        }

        // TD from tag webhook
        if (filament && filament.td && filament.td > 0) {
            addField(fields, 'TD', filament.td + ' mm');
        }

        // Emoji + Custom Message from TigerTag metadata field
        if (filament && filament.emoji && filament.emoji.trim() !== '') {
            addField(fields, 'Emoji', filament.emoji.trim());
        }
        if (filament && filament.message && filament.message.trim() !== '') {
            addField(fields, 'Message', filament.message.trim());
        }

        // UID
        var uid = mk.CARD_UID;
        if (tag && tag.scan && tag.scan.uid) {
            uid = tag.scan.uid;
        }
        if (uid && uid !== 0) {
            var uidStr = Array.isArray(uid) ? formatUid(uid) : escapeHtml(uid);
            fields.push({
                label: 'UID',
                value: '<span class="uid-value">' + uidStr + '</span>',
                raw: true
            });
        }

        // Render fields
        var grid = document.createElement('div');
        grid.className = 'field-grid';

        for (var i = 0; i < fields.length; i++) {
            var fl = document.createElement('span');
            fl.className = 'field-label';
            fl.textContent = fields[i].label;

            var fv = document.createElement('span');
            fv.className = 'field-value';
            if (fields[i].raw) {
                fv.innerHTML = fields[i].value;
            } else {
                fv.textContent = fields[i].value;
            }

            grid.appendChild(fl);
            grid.appendChild(fv);
        }

        body.appendChild(grid);
    }

    card.appendChild(body);
    return card;
}

function scanAll() {
    var btn = document.getElementById('scan-btn');
    btn.disabled = true;
    btn.textContent = 'Scanning…';
    fetch('/spools/api/scan', { method: 'POST' })
        .then(function (resp) { return resp.json(); })
        .then(function () {
            // Give OpenRFID ~3s to read and fire the webhook
            setTimeout(function () {
                fetchChannels();
                btn.disabled = false;
                btn.textContent = 'Scan All';
            }, 3000);
        })
        .catch(function (err) {
            console.error('Scan failed:', err);
            btn.disabled = false;
            btn.textContent = 'Scan All';
        });
}

function fetchChannels() {
    fetch('/spools/api/channels')
        .then(function (resp) {
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            return resp.json();
        })
        .then(function (data) {
            setConnectionStatus(true);
            var container = document.getElementById('channels');
            container.innerHTML = '';
            var channels = data.channels || [];
            for (var i = 0; i < channels.length; i++) {
                container.appendChild(renderChannel(channels[i]));
            }
        })
        .catch(function (err) {
            setConnectionStatus(false);
            console.error('Failed to fetch channels:', err);
        });
}

function init() {
    fetchChannels();
    pollTimer = setInterval(fetchChannels, POLL_INTERVAL);
}

document.addEventListener('DOMContentLoaded', init);
