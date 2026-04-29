'use strict';

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

function formatUid(uidArray) {
    if (!uidArray || !Array.isArray(uidArray)) return '—';
    return uidArray.map(function (b) { return ('0' + b.toString(16)).slice(-2).toUpperCase(); }).join(':');
}

function colorToHex(rgb) {
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
