'use strict';

// ── Tag mapping config page ──────────────────────────────────────────────────
// Markup lives in pages/config-tag-mapping.html
// (templates "config-mapping-block" + "config-mapping-row").

var TagMappingConfigPage = (function () {

    function mount(container) {
        var config = App.getConfig();
        var tagMappings = Array.isArray(config.tag_mappings) ? config.tag_mappings : [];

        var page = ConfigShared.buildPageShell('Tag Mapping');

        var section = document.createElement('div');
        section.className = 'config-section';
        section.appendChild(buildMappingBlock(tagMappings));
        page.appendChild(section);

        page.appendChild(ConfigShared.buildSaveFooter(function (saveBtn, statusEl) {
            ConfigShared.saveConfigPartial(
                { tag_mappings: collectTagMappings(section) },
                saveBtn, statusEl
            );
        }));

        container.appendChild(page);
    }

    function unmount() {}

    function buildMappingBlock(mappingRows) {
        var srcFields = ConfigShared.SOURCE_FIELDS;

        var block = Templates.clone('config-mapping-block');
        var table = Templates.$(block, '[data-id="table"]');
        var addBtn = Templates.$(block, '[data-id="add-row"]');

        function addRow(toVal, fromVal) {
            var row = Templates.clone('config-mapping-row');
            var toSlot = Templates.$(row, '[data-id="to-slot"]');
            var fromSlot = Templates.$(row, '[data-id="from-slot"]');

            toSlot.replaceWith(ConfigShared.buildSelect(ConfigShared.GENERIC_FIELDS, toVal, 'mapping-to'));
            fromSlot.replaceWith(ConfigShared.buildSelect(srcFields, fromVal, 'mapping-from'));

            Templates.on(row, '[data-id="remove"]', 'click', function () {
                table.removeChild(row);
            });

            table.appendChild(row);
        }

        mappingRows.forEach(function (r) { addRow(r.to, r.from); });

        addBtn.addEventListener('click', function () {
            addRow(ConfigShared.GENERIC_FIELDS[0].value, srcFields[0].value);
        });

        return block;
    }

    function collectTagMappings(section) {
        var rows = [];
        section.querySelectorAll('.mapping-row').forEach(function (row) {
            var toSel = row.querySelector('.mapping-to');
            var fromSel = row.querySelector('.mapping-from');
            if (toSel && fromSel && toSel.value && fromSel.value) {
                rows.push({ to: toSel.value, from: fromSel.value });
            }
        });
        return rows;
    }

    return { mount: mount, unmount: unmount };
})();
