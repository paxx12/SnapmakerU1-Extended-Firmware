'use strict';

// ── Slot config page ─────────────────────────────────────────────────────────
// Markup lives in pages/config-slots.html (template id "config-slots-row").
// The outer page shell and save footer are still provided by ConfigShared.

var SlotConfigPage = (function () {

    function mount(container) {
        var config = App.getConfig();
        var slotNames = config.slot_names || {};
        var slotNotes = config.slot_notes || {};

        var page = ConfigShared.buildPageShell('Slot Config');

        var section = document.createElement('div');
        section.className = 'config-section';

        for (var i = 0; i < 4; i++) {
            section.appendChild(buildSlotRow(i, slotNames, slotNotes));
        }
        page.appendChild(section);

        page.appendChild(ConfigShared.buildSaveFooter(function (saveBtn, statusEl) {
            var newNames = {};
            var newNotes = {};
            page.querySelectorAll('input[data-config-key="slot_names"]').forEach(function (inp) {
                newNames[inp.dataset.slot] = inp.value.trim();
            });
            page.querySelectorAll('textarea[data-config-key="slot_notes"]').forEach(function (inp) {
                newNotes[inp.dataset.slot] = inp.value.trim();
            });
            ConfigShared.saveConfigPartial({ slot_names: newNames, slot_notes: newNotes }, saveBtn, statusEl);
        }));

        container.appendChild(page);
    }

    function unmount() {}

    function buildSlotRow(index, slotNames, slotNotes) {
        var defaultName = ConfigShared.DEFAULT_NAMES[index];
        var row = Templates.clone('config-slots-row');
        row.dataset.slot = index;

        Templates.setText(row, '[data-id="slot-label"]', defaultName);

        var nameInput = Templates.$(row, '[data-id="name-input"]');
        nameInput.placeholder = defaultName;
        nameInput.value = slotNames[index] || slotNames[String(index)] || '';
        nameInput.dataset.slot = index;

        var noteInput = Templates.$(row, '[data-id="note-input"]');
        noteInput.value = slotNotes[index] || slotNotes[String(index)] || '';
        noteInput.dataset.slot = index;

        return row;
    }

    return { mount: mount, unmount: unmount };
})();
