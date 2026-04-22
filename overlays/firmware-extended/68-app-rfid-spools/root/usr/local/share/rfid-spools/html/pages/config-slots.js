'use strict';

// ── Slot config page ─────────────────────────────────────────────────────────

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
        var defaultNames = ConfigShared.DEFAULT_NAMES;
        var row = document.createElement('div');
        row.className = 'config-slot-row';
        row.dataset.slot = index;

        var slotLabel = document.createElement('div');
        slotLabel.className = 'config-slot-label';
        slotLabel.textContent = defaultNames[index];
        row.appendChild(slotLabel);

        var fields = document.createElement('div');
        fields.className = 'config-slot-fields';

        var nameLabel = document.createElement('label');
        nameLabel.className = 'config-field-label';
        nameLabel.textContent = 'Custom name';
        var nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.className = 'config-input';
        nameInput.placeholder = defaultNames[index];
        nameInput.value = slotNames[index] || slotNames[String(index)] || '';
        nameInput.dataset.configKey = 'slot_names';
        nameInput.dataset.slot = index;
        nameLabel.appendChild(nameInput);
        fields.appendChild(nameLabel);

        var noteLabel = document.createElement('label');
        noteLabel.className = 'config-field-label';
        noteLabel.textContent = 'Note';
        var noteInput = document.createElement('textarea');
        noteInput.className = 'config-textarea';
        noteInput.placeholder = 'e.g. backup spool, low remaining\u2026';
        noteInput.rows = 2;
        noteInput.value = slotNotes[index] || slotNotes[String(index)] || '';
        noteInput.dataset.configKey = 'slot_notes';
        noteInput.dataset.slot = index;
        noteLabel.appendChild(noteInput);
        fields.appendChild(noteLabel);

        row.appendChild(fields);
        return row;
    }

    return { mount: mount, unmount: unmount };
})();
