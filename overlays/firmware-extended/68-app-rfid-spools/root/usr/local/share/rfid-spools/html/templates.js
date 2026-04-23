'use strict';

// ── Template loader ──────────────────────────────────────────────────────────
// Loads HTML files containing one or more <template id="..."> elements,
// indexes them by id, and serves cloned copies to page modules.
//
// Usage:
//   Templates.loadAll(['pages/spools.html', ...]).then(...)
//   var node = Templates.clone('spools-page');
//   Templates.setText(node, '[data-id=title]', 'Hello');

var Templates = (function () {

    var _byId = {};
    var _loaded = {};

    function loadAll(urls) {
        return Promise.all(urls.map(load));
    }

    function load(url) {
        if (_loaded[url]) return _loaded[url];
        _loaded[url] = fetch(url, { cache: 'no-cache' })
            .then(function (r) {
                if (!r.ok) throw new Error('Failed to load template ' + url + ': ' + r.status);
                return r.text();
            })
            .then(function (html) {
                var doc = new DOMParser().parseFromString(html, 'text/html');
                doc.querySelectorAll('template[id]').forEach(function (tpl) {
                    if (_byId[tpl.id]) {
                        console.warn('Template id collision: ' + tpl.id);
                    }
                    _byId[tpl.id] = tpl;
                });
            });
        return _loaded[url];
    }

    function get(id) {
        var tpl = _byId[id];
        if (!tpl) throw new Error('Unknown template: ' + id);
        return tpl;
    }

    // Clone the first child element of a template. Use this when the template
    // wraps a single root element (the common case).
    function clone(id) {
        var tpl = get(id);
        var first = tpl.content.firstElementChild;
        if (!first) throw new Error('Template ' + id + ' has no element child');
        return first.cloneNode(true);
    }

    // Clone the entire template content as a DocumentFragment.
    function cloneFragment(id) {
        return get(id).content.cloneNode(true);
    }

    function $(root, sel) {
        return sel ? root.querySelector(sel) : root;
    }

    function $$(root, sel) {
        return Array.prototype.slice.call(root.querySelectorAll(sel));
    }

    function setText(root, sel, val) {
        var el = $(root, sel);
        if (el) el.textContent = (val === undefined || val === null) ? '' : String(val);
        return el;
    }

    function setAttr(root, sel, name, val) {
        var el = $(root, sel);
        if (!el) return null;
        if (val === null || val === undefined || val === false) {
            el.removeAttribute(name);
        } else {
            el.setAttribute(name, val === true ? '' : String(val));
        }
        return el;
    }

    function on(root, sel, event, handler) {
        var el = $(root, sel);
        if (el) el.addEventListener(event, handler);
        return el;
    }

    return {
        loadAll: loadAll,
        load: load,
        clone: clone,
        cloneFragment: cloneFragment,
        $: $,
        $$: $$,
        setText: setText,
        setAttr: setAttr,
        on: on
    };
})();
