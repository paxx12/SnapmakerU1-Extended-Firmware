'use strict';

// ── App entry point ──────────────────────────────────────────────────────────
// Owns shared state: connection status and config cache.

var App = (function () {

    var _config = {};

    function getConfig() { return _config; }
    function setConfig(cfg) { _config = cfg || {}; }

    function setConnectionStatus(connected) {
        var dot = document.getElementById('connection-status');
        var text = document.getElementById('connection-text');
        if (dot) dot.className = 'status-dot ' + (connected ? 'connected' : 'disconnected');
        if (text) text.textContent = connected ? 'RFID: Connected' : 'RFID: Disconnected';
    }

    function loadConfig() {
        return fetch('/spools/api/config')
            .then(function (resp) { return resp.ok ? resp.json() : {}; })
            .then(function (cfg) { _config = cfg || {}; })
            .catch(function () { _config = {}; });
    }

    function init() {
        Promise.all([
            loadConfig(),
            Templates.loadAll([
                'pages/config-shared.html',
                'pages/config-slots.html',
                'pages/config-spoolman.html',
                'pages/spools.html'
            ])
        ]).then(function () {
            Router.init();
        });
    }

    return { init: init, getConfig: getConfig, setConfig: setConfig, setConnectionStatus: setConnectionStatus, navigate: function (page) { Router.navigate(page); } };
})();

document.addEventListener('DOMContentLoaded', function () {
    App.init();
});
