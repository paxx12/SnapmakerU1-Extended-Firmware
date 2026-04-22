'use strict';

// ── Router ───────────────────────────────────────────────────────────────────
// Manages sidebar navigation and mounts/unmounts page modules.

var Router = (function () {

    var currentPage = null;

    var pages = {
        spools: {
            label: 'Spools',
            icon: '🧵',
            module: function () { return SpoolsPage; },
            headerButtons: ['scan-btn']
        },
        'config-spoolman': {
            label: 'Spoolman',
            icon: '🔗',
            module: function () { return SpoolmanConfigPage; },
            headerButtons: []
        },
        'config-slots': {
            label: 'Slot config',
            icon: '🗂️',
            module: function () { return SlotConfigPage; },
            headerButtons: []
        },
        'config-mapping': {
            label: 'Tag mapping',
            icon: '🏷️',
            module: function () { return TagMappingConfigPage; },
            headerButtons: []
        }
    };

    var pageOrder = ['spools', 'config-spoolman', 'config-slots', 'config-mapping'];

    function navigate(pageKey) {
        if (currentPage === pageKey) return;

        // Unmount current
        if (currentPage && pages[currentPage]) {
            pages[currentPage].module().unmount();
        }

        currentPage = pageKey;

        // Update active nav item
        pageOrder.forEach(function (key) {
            var item = document.getElementById('nav-' + key);
            if (item) item.className = 'nav-item' + (key === pageKey ? ' active' : '');
        });

        // Mount new page
        var content = document.getElementById('content');
        content.innerHTML = '';

        var def = pages[pageKey];
        if (def) {
            def.module().mount(content);
        }

        // Show/hide header buttons
        Object.keys(pages).forEach(function (key) {
            (pages[key].headerButtons || []).forEach(function (btnId) {
                var btn = document.getElementById(btnId);
                if (btn) btn.style.display = '';
            });
        });
        // Hide buttons not belonging to this page
        var activeButtons = def ? (def.headerButtons || []) : [];
        pageOrder.forEach(function (key) {
            (pages[key].headerButtons || []).forEach(function (btnId) {
                if (activeButtons.indexOf(btnId) === -1) {
                    var btn = document.getElementById(btnId);
                    if (btn) btn.style.display = 'none';
                }
            });
        });
    }

    function buildSidebar() {
        var sidebar = document.getElementById('sidebar');
        if (!sidebar) return;
        sidebar.innerHTML = '';

        pageOrder.forEach(function (key) {
            var def = pages[key];
            var item = document.createElement('button');
            item.id = 'nav-' + key;
            item.className = 'nav-item';
            item.innerHTML = '<span class="nav-icon">' + def.icon + '</span><span class="nav-label">' + escapeHtml(def.label) + '</span>';
            item.addEventListener('click', function () { navigate(key); });
            sidebar.appendChild(item);
        });
    }

    function init() {
        buildSidebar();
        navigate('spools');
    }

    return { init: init, navigate: navigate };
})();
