'use strict';

// ── Tag mapping config page ───────────────────────────────────────────────────

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

        var block = document.createElement('div');
        block.className = 'mapping-block';

        var table = document.createElement('div');
        table.className = 'mapping-table';
        block.appendChild(table);

        function addRow(toVal, fromVal) {
            var row = document.createElement('div');
            row.className = 'mapping-row';

            var toSel = ConfigShared.buildSelect(ConfigShared.GENERIC_FIELDS, toVal, 'mapping-to');
            var arrow = document.createElement('span');
            arrow.className = 'mapping-arrow';
            arrow.textContent = '\u2190';
            var fromSel = ConfigShared.buildSelect(srcFields, fromVal, 'mapping-from');

            var removeBtn = document.createElement('button');
            removeBtn.className = 'mapping-remove-btn';
            removeBtn.textContent = '\u00d7';
            removeBtn.title = 'Remove row';
            removeBtn.addEventListener('click', function () { table.removeChild(row); });

            row.appendChild(toSel);
            row.appendChild(arrow);
            row.appendChild(fromSel);
            row.appendChild(removeBtn);
            table.appendChild(row);
        }

        mappingRows.forEach(function (r) { addRow(r.to, r.from); });

        var addBtn = document.createElement('button');
        addBtn.className = 'mapping-add-btn';
        addBtn.textContent = '+ Add row';
        addBtn.addEventListener('click', function () {
            addRow(ConfigShared.GENERIC_FIELDS[0].value, srcFields[0].value);
        });
        block.appendChild(addBtn);

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
