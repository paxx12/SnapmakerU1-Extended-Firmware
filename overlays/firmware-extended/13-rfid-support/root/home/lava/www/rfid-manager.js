// RFID Tag Manager JavaScript

// API base URL (relative to current origin)
const API_BASE = '/server/rfid';

// Material default temperatures (for reference)
const MATERIAL_DEFAULTS = {
    'PLA': { min_temp: 190, max_temp: 220, bed_min_temp: 50, bed_max_temp: 70, density: 1.24 },
    'PETG': { min_temp: 220, max_temp: 250, bed_min_temp: 70, bed_max_temp: 90, density: 1.27 },
    'ABS': { min_temp: 230, max_temp: 260, bed_min_temp: 90, bed_max_temp: 110, density: 1.04 },
    'TPU': { min_temp: 210, max_temp: 230, bed_min_temp: 40, bed_max_temp: 60, density: 1.21 },
    'PVA': { min_temp: 190, max_temp: 210, bed_min_temp: 50, bed_max_temp: 70, density: 1.19 },
    'NYLON': { min_temp: 240, max_temp: 270, bed_min_temp: 70, bed_max_temp: 90, density: 1.14 },
    'ASA': { min_temp: 240, max_temp: 260, bed_min_temp: 90, bed_max_temp: 110, density: 1.07 },
    'PC': { min_temp: 260, max_temp: 290, bed_min_temp: 100, bed_max_temp: 120, density: 1.20 }
};

// State
let channelsData = [];
let colorPickers = {};
let userModifiedColors = new Set(); // Track which additional colors the user has actually set

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeColorPickers();
    initializeEventListeners();
    refreshAllChannels();
});

// Pickr configuration for main color picker (with alpha)
function createPickr(el, defaultColor, hasAlpha = true) {
    return Pickr.create({
        el: el,
        theme: 'nano',
        default: defaultColor,
        useAsButton: false,
        swatches: [
            '#FFFFFFFF', '#000000FF', '#FF0000FF', '#00FF00FF', '#0000FFFF',
            '#FFFF00FF', '#FF00FFFF', '#00FFFFFF', '#FFA500FF', '#808080FF'
        ],
        components: {
            preview: true,
            opacity: hasAlpha,
            hue: true,
            interaction: {
                hex: true,
                rgba: hasAlpha,
                input: true,
                save: false  // No save button - changes sync in real time
            }
        }
    });
}

// Initialize all color pickers
function initializeColorPickers() {
    const colorHex = document.getElementById('color-hex');

    // Main color picker with alpha
    colorPickers.main = createPickr('#color-picker', '#FFFFFFFF', true);

    // Real-time sync: picker changes update the hex input and button preview immediately
    colorPickers.main.on('change', (color) => {
        if (color) {
            // toHEXA() returns array of hex chars, join to get string
            const hexArr = color.toHEXA();
            const hexStr = hexArr.join('').toUpperCase();
            colorHex.value = hexStr;
            // Update button preview (needed when save button is disabled)
            colorPickers.main.applyColor();
        }
    });

    // Normalize input on typing (strip #, uppercase)
    colorHex.addEventListener('input', (e) => {
        const normalized = e.target.value.replace(/^#/, '').toUpperCase();
        e.target.value = normalized;
    });

    // Sync hex input to picker on blur (when user finishes typing)
    colorHex.addEventListener('blur', (e) => {
        const value = e.target.value;
        // Accept 6-char (RRGGBB) or 8-char (RRGGBBAA) hex
        if (/^[0-9A-Fa-f]{6}$/.test(value)) {
            colorPickers.main.setColor('#' + value + 'FF', true);
            colorPickers.main.applyColor();  // Update button preview
        } else if (/^[0-9A-Fa-f]{8}$/.test(value)) {
            colorPickers.main.setColor('#' + value, true);
            colorPickers.main.applyColor();  // Update button preview
        }
    });

    // Additional color pickers (no alpha)
    for (let i = 2; i <= 5; i++) {
        const pickerEl = `#color${i}-picker`;
        const hexInput = document.getElementById(`color${i}-hex`);
        const colorKey = `color${i}`;

        colorPickers[colorKey] = createPickr(pickerEl, '#FFFFFF', false);

        // Track user interaction with picker - mark as modified when user opens/interacts
        colorPickers[colorKey].on('show', () => {
            // Mark as modified when user opens the picker
            userModifiedColors.add(colorKey);
        });

        // Real-time sync for additional colors
        colorPickers[colorKey].on('change', (color) => {
            if (color) {
                // toHEXA() returns array of hex chars, join and take first 6 for RGB
                const hexArr = color.toHEXA();
                const hexStr = hexArr.join('').substring(0, 6).toUpperCase();
                // Only update input if user has interacted with this color
                if (userModifiedColors.has(colorKey)) {
                    hexInput.value = hexStr;
                }
                // Update button preview (needed when save button is disabled)
                colorPickers[colorKey].applyColor();
            }
        });

        // Normalize input on typing - mark as modified when user types
        hexInput.addEventListener('input', (e) => {
            const normalized = e.target.value.replace(/^#/, '').toUpperCase();
            e.target.value = normalized;
            if (normalized !== '') {
                userModifiedColors.add(colorKey);
            }
        });

        // Sync hex input to picker on blur
        hexInput.addEventListener('blur', (e) => {
            const normalized = e.target.value;
            if (/^[0-9A-Fa-f]{6}$/.test(normalized)) {
                userModifiedColors.add(colorKey);
                colorPickers[colorKey].setColor('#' + normalized, true);
                colorPickers[colorKey].applyColor();  // Update button preview
            } else if (normalized === '') {
                // If user cleared the input, remove from modified set and reset picker to white (visual only)
                userModifiedColors.delete(colorKey);
                colorPickers[colorKey].setColor('#FFFFFF', true);
                colorPickers[colorKey].applyColor();
            }
        });
    }
}

// Event Listeners
function initializeEventListeners() {
    document.getElementById('refresh-all').addEventListener('click', refreshAllChannels);
    document.getElementById('write-form').addEventListener('submit', handleWriteTag);
    document.getElementById('erase-form').addEventListener('submit', handleEraseTag);

    // Pre-populate form and update button states when write channel changes
    const writeChannelSelect = document.querySelector('#write-form select[name="channel"]');
    writeChannelSelect.addEventListener('change', (e) => {
        const channel = parseInt(e.target.value);
        populateWriteFormFromChannel(channel);
        updateButtonStates();
    });

    // Update button states when erase channel changes
    const eraseChannelSelect = document.querySelector('#erase-form select[name="channel"]');
    eraseChannelSelect.addEventListener('change', updateButtonStates);

    // Auto-fill defaults when material type changes
    const typeSelect = document.querySelector('#write-form select[name="type"]');
    typeSelect.addEventListener('change', (e) => {
        const material = e.target.value;
        const defaults = MATERIAL_DEFAULTS[material];
        if (defaults) {
            const form = document.getElementById('write-form');
            form.querySelector('input[name="density"]').placeholder = `Auto (${defaults.density})`;
            form.querySelector('input[name="min_temp"]').placeholder = `Auto (${defaults.min_temp})`;
            form.querySelector('input[name="max_temp"]').placeholder = `Auto (${defaults.max_temp})`;
            form.querySelector('input[name="bed_min_temp"]').placeholder = `Auto (${defaults.bed_min_temp})`;
            form.querySelector('input[name="bed_max_temp"]').placeholder = `Auto (${defaults.bed_max_temp})`;
        }
    });
}

// API Calls
async function apiCall(endpoint, method = 'GET', data = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json'
        }
    };

    if (data && method !== 'GET') {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || `HTTP ${response.status}`);
        }

        return result;
    } catch (error) {
        console.error('API call failed:', error);
        throw error;
    }
}

// Channel Management
async function refreshAllChannels() {
    try {
        showStatus('Refreshing channels...', 'info');
        const response = await apiCall('/tags');
        // Moonraker wraps response in {result: {...}}
        channelsData = response.result?.channels || response.channels;
        renderChannels();
        showStatus('Channels refreshed successfully', 'success');
    } catch (error) {
        showStatus(`Failed to refresh channels: ${error.message}`, 'error');
    }
}

async function refreshSingleChannel(channel) {
    try {
        const response = await apiCall(`/tags/${channel}`);
        // Moonraker wraps response in {result: {...}}
        const channelData = response.result || response;

        // Update the specific channel in our data
        const index = channelsData.findIndex(c => c.channel === channel);
        if (index !== -1) {
            channelsData[index] = channelData;
        } else {
            channelsData.push(channelData);
        }

        // Re-render channels
        renderChannels();
    } catch (error) {
        const errorMsg = error.message || (typeof error === 'string' ? error : JSON.stringify(error));
        showStatus(`Failed to refresh channel ${channel}: ${errorMsg}`, 'error');
    }
}

function renderChannels() {
    const grid = document.getElementById('channels-grid');
    grid.innerHTML = '';

    channelsData.forEach(channel => {
        const card = createChannelCard(channel);
        grid.appendChild(card);
    });

    // Auto-populate write form for currently selected channel
    const writeChannelSelect = document.querySelector('#write-form select[name="channel"]');
    if (writeChannelSelect) {
        const selectedChannel = parseInt(writeChannelSelect.value);
        populateWriteFormFromChannel(selectedChannel);
    }

    // Update button states based on current channel data
    updateButtonStates();
}

function populateWriteFormFromChannel(channel) {
    const channelData = channelsData.find(c => c.channel === channel);
    if (!channelData) return;

    const form = document.getElementById('write-form');
    const filament = channelData.filament || {};

    // Clear user-modified tracking - we'll re-add colors that exist on the tag
    userModifiedColors.clear();

    // Helper to check if a value is valid (not empty, not "NONE", not 0)
    const hasValue = (val) => {
        if (!val) return false;
        if (typeof val === 'string' && (val.trim() === '' || val.toUpperCase() === 'NONE')) return false;
        if (typeof val === 'number' && val === 0) return false;
        return true;
    };

    // Populate form with available data, use defaults for missing fields
    // Material type: use tag data if available, otherwise default to PLA
    const materialType = hasValue(filament.type) ? filament.type : 'PLA';
    form.querySelector('select[name="type"]').value = materialType;
    form.querySelector('select[name="type"]').dispatchEvent(new Event('change'));

    // Brand: use tag data if available, otherwise default to 'Generic'
    form.querySelector('input[name="brand"]').value = hasValue(filament.brand) ? filament.brand : 'Generic';

    // Subtype: use tag data if available, otherwise clear
    form.querySelector('input[name="subtype"]').value = hasValue(filament.subtype) ? filament.subtype : '';

    // Color: use tag data if available, otherwise default to white (RRGGBBAA format)
    const hexColor = hasValue(filament.color_hex) ? filament.color_hex.toUpperCase() : 'FFFFFF';
    const alphaValue = hasValue(filament.alpha) ? filament.alpha.toUpperCase() : 'FF';
    const fullColor = hexColor + alphaValue;  // Combined RRGGBBAA
    form.querySelector('input[name="color_hex"]').value = fullColor;
    if (colorPickers.main) {
        colorPickers.main.setColor('#' + fullColor, true);
        colorPickers.main.applyColor();  // Update button preview
    }

    // Additional colors: use tag data if available, otherwise leave empty
    const additionalColors = filament.additional_color_hexes || [];
    for (let i = 0; i < 4; i++) {
        const colorHexInput = document.getElementById(`color${i + 2}-hex`);
        const pickerKey = `color${i + 2}`;
        if (colorHexInput) {
            if (i < additionalColors.length && additionalColors[i]) {
                const hexVal = additionalColors[i].toUpperCase();
                colorHexInput.value = hexVal;
                userModifiedColors.add(pickerKey); // Mark as modified since it came from the tag
                if (colorPickers[pickerKey]) {
                    colorPickers[pickerKey].setColor('#' + hexVal, true);
                    colorPickers[pickerKey].applyColor();  // Update button preview
                }
            } else {
                // Leave input empty and remove from modified set
                colorHexInput.value = '';
                userModifiedColors.delete(pickerKey);
                if (colorPickers[pickerKey]) {
                    colorPickers[pickerKey].setColor('#FFFFFF', true);
                    colorPickers[pickerKey].applyColor();
                }
            }
        }
    }

    // Diameter: use tag data if available, otherwise default to 1.75mm
    form.querySelector('input[name="diameter"]').value = hasValue(filament.diameter) ? filament.diameter : '1.75';

    // Density: use tag data if available, otherwise clear (auto-fill from material)
    form.querySelector('input[name="density"]').value = hasValue(filament.density) ? filament.density : '';

    // Temperatures: use tag data if available, otherwise clear (auto-fill from material)
    form.querySelector('input[name="min_temp"]').value = hasValue(filament.min_temp) ? filament.min_temp : '';
    form.querySelector('input[name="max_temp"]').value = hasValue(filament.max_temp) ? filament.max_temp : '';

    // Bed temperatures: use min/max if available, otherwise fall back to bed_temp
    if (hasValue(filament.bed_min_temp)) {
        form.querySelector('input[name="bed_min_temp"]').value = filament.bed_min_temp;
    } else if (hasValue(filament.bed_temp)) {
        form.querySelector('input[name="bed_min_temp"]').value = filament.bed_temp;
    } else {
        form.querySelector('input[name="bed_min_temp"]').value = '';
    }

    if (hasValue(filament.bed_max_temp)) {
        form.querySelector('input[name="bed_max_temp"]').value = filament.bed_max_temp;
    } else if (hasValue(filament.bed_temp)) {
        form.querySelector('input[name="bed_max_temp"]').value = filament.bed_temp;
    } else {
        form.querySelector('input[name="bed_max_temp"]').value = '';
    }

    // Weight: use tag data if available, otherwise clear
    form.querySelector('input[name="weight"]').value = hasValue(filament.weight) ? filament.weight : '';
}

function createChannelCard(channel) {
    const card = document.createElement('div');
    card.className = 'channel-card';

    const tagPresent = channel.tag_present;
    const tagEmpty = channel.tag_empty;

    let statusClass, statusText;
    if (tagEmpty) {
        statusClass = 'empty';
        statusText = 'Empty Tag';
    } else if (tagPresent) {
        statusClass = 'present';
        statusText = 'Tag Present';
    } else {
        statusClass = 'absent';
        statusText = 'No Tag';
    }

    let content = `
        <div class="channel-header">
            <div class="channel-title">Channel ${channel.channel}</div>
            <div class="tag-status ${statusClass}">${statusText}</div>
        </div>
    `;

    if (tagPresent) {
        const filament = channel.filament || {};

        content += '<div class="tag-info">';

        // Show message for empty tags
        if (tagEmpty) {
            content += `
                <div class="info-row">
                    <span class="info-label" style="grid-column: 1 / -1;">Tag detected but not programmed. Use the Tag Operations block to add filament information.</span>
                </div>
            `;
        }

        // Filament info (only if tag is programmed) - FIRST
        if (!tagEmpty && (filament.brand || filament.type)) {
            // Build filament description: "Brand Type (Subtype)" or "Brand Type" if no subtype
            let filamentDesc = `${filament.brand || 'Unknown'} ${filament.type || ''}`;
            if (filament.subtype && filament.subtype !== 'Basic' && filament.subtype !== 'Reserved') {
                filamentDesc += ` (${filament.subtype})`;
            }
            content += `
                <div class="info-row">
                    <span class="info-label">Filament</span>
                    <span class="info-value">${filamentDesc}</span>
                </div>
            `;
        }

        if (!tagEmpty && filament.color_hex) {
            // Build color display with all colors
            let colorSwatches = `<span class="color-swatch" style="background-color: #${filament.color_hex};"></span>`;
            let colorText = `#${filament.color_hex}`;

            // Add alpha info if present and not fully opaque
            if (filament.alpha && filament.alpha !== 'FF') {
                colorText += ` (${filament.alpha} alpha)`;
            }

            // Add additional colors if present
            if (filament.additional_color_hexes && filament.additional_color_hexes.length > 0) {
                filament.additional_color_hexes.forEach(hex => {
                    colorSwatches += `<span class="color-swatch" style="background-color: #${hex};"></span>`;
                });
            }

            content += `
                <div class="info-row">
                    <span class="info-label">Color</span>
                    <span class="info-value color-value">
                        ${colorText}
                        <span class="color-swatches">${colorSwatches}</span>
                    </span>
                </div>
            `;
        }

        if (!tagEmpty && filament.diameter) {
            content += `
                <div class="info-row">
                    <span class="info-label">Diameter</span>
                    <span class="info-value">${filament.diameter} mm</span>
                </div>
            `;
        }

        if (!tagEmpty && filament.density) {
            content += `
                <div class="info-row">
                    <span class="info-label">Density</span>
                    <span class="info-value">${filament.density} g/cm³</span>
                </div>
            `;
        }

        // Weight - show in kg if 1000g or more
        if (!tagEmpty && filament.weight) {
            let weightDisplay;
            if (filament.weight >= 1000) {
                const kg = filament.weight / 1000;
                // Show 1 decimal if needed (1.5kg), otherwise show as integer (1kg)
                weightDisplay = kg % 1 === 0 ? `${kg} kg` : `${kg.toFixed(1)} kg`;
            } else {
                weightDisplay = `${filament.weight} g`;
            }
            content += `
                <div class="info-row">
                    <span class="info-label">Spool Weight</span>
                    <span class="info-value">${weightDisplay}</span>
                </div>
            `;
        }

        // Temperature info
        if (!tagEmpty && filament.min_temp && filament.max_temp) {
            content += `
                <div class="info-row">
                    <span class="info-label">Extruder Temp</span>
                    <span class="info-value">${filament.min_temp}°C - ${filament.max_temp}°C</span>
                </div>
            `;
        }

        // Bed temperature - show range if min/max available, otherwise single value
        if (!tagEmpty && (filament.bed_min_temp || filament.bed_max_temp || filament.bed_temp)) {
            let bedTempDisplay;
            if (filament.bed_min_temp && filament.bed_max_temp && filament.bed_min_temp !== filament.bed_max_temp) {
                bedTempDisplay = `${filament.bed_min_temp}°C - ${filament.bed_max_temp}°C`;
            } else if (filament.bed_min_temp) {
                bedTempDisplay = `${filament.bed_min_temp}°C`;
            } else if (filament.bed_max_temp) {
                bedTempDisplay = `${filament.bed_max_temp}°C`;
            } else {
                bedTempDisplay = `${filament.bed_temp}°C`;
            }
            content += `
                <div class="info-row">
                    <span class="info-label">Bed Temp</span>
                    <span class="info-value">${bedTempDisplay}</span>
                </div>
            `;
        }

        // Tag type and UID at the bottom
        if (channel.tag_type) {
            content += `
                <div class="info-row">
                    <span class="info-label">Tag Type</span>
                    <span class="info-value">${channel.tag_type}</span>
                </div>
            `;
        }

        if (channel.uid) {
            content += `
                <div class="info-row">
                    <span class="info-label">UID</span>
                    <span class="info-value">${channel.uid}</span>
                </div>
            `;
        }

        content += '</div>';
    } else {
        content += '<div class="no-tag">No RFID tag detected on this channel</div>';
    }

    card.innerHTML = content;
    return card;
}

// Form Handlers
async function handleWriteTag(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    const materialType = formData.get('type');
    const defaults = MATERIAL_DEFAULTS[materialType] || {};

    // Parse color_hex which may be 6-char (RRGGBB) or 8-char (RRGGBBAA)
    const rawColorHex = formData.get('color_hex').replace(/^#/, '').toUpperCase();
    const colorHex = rawColorHex.substring(0, 6);  // First 6 chars are RGB
    const alphaHex = rawColorHex.length >= 8 ? rawColorHex.substring(6, 8) : 'FF';  // Last 2 chars are alpha, default FF

    const data = {
        channel: parseInt(formData.get('channel')),
        type: materialType,
        brand: formData.get('brand'),
        color_hex: colorHex,
        diameter: parseFloat(formData.get('diameter'))
    };

    // Optional fields
    if (formData.get('subtype')) {
        data.subtype = formData.get('subtype');
    }

    // Density: use form value or auto default
    if (formData.get('density')) {
        data.density = parseFloat(formData.get('density'));
    } else if (defaults.density) {
        data.density = defaults.density;
    }

    // Extruder temperatures: use form value or auto default
    if (formData.get('min_temp')) {
        data.min_temp = parseInt(formData.get('min_temp'));
    } else if (defaults.min_temp) {
        data.min_temp = defaults.min_temp;
    }
    if (formData.get('max_temp')) {
        data.max_temp = parseInt(formData.get('max_temp'));
    } else if (defaults.max_temp) {
        data.max_temp = defaults.max_temp;
    }

    // Alpha transparency - send as hex string (G-code command expects 2-digit hex)
    if (alphaHex && alphaHex !== 'FF') {
        data.alpha = alphaHex;  // e.g., "73" for 115 decimal
    }

    // Additional colors (only include if user has explicitly set them)
    for (let i = 2; i <= 5; i++) {
        const colorKey = `color${i}`;
        const colorVal = formData.get(colorKey);
        // Only include color if user has modified it (opened picker or typed)
        if (userModifiedColors.has(colorKey) && colorVal) {
            const normalized = colorVal.replace(/^#/, '').toUpperCase();
            if (normalized) {
                data[colorKey] = normalized;
            }
        }
    }

    // Bed temperatures: use form value or auto default
    if (formData.get('bed_min_temp')) {
        data.bed_min_temp = parseInt(formData.get('bed_min_temp'));
    } else if (defaults.bed_min_temp) {
        data.bed_min_temp = defaults.bed_min_temp;
    }
    if (formData.get('bed_max_temp')) {
        data.bed_max_temp = parseInt(formData.get('bed_max_temp'));
    } else if (defaults.bed_max_temp) {
        data.bed_max_temp = defaults.bed_max_temp;
    }

    // Weight
    if (formData.get('weight')) {
        data.weight = parseFloat(formData.get('weight'));
    }

    try {
        showStatus('Writing tag...', 'info');
        const response = await apiCall('/write_openspool', 'POST', data);
        // Moonraker wraps response in {result: {...}}
        const result = response.result || response;

        if (result.success) {
            const verifyMsg = result.verified ? ' and verified' : ' (verification pending)';
            showStatus(`Tag written${verifyMsg} successfully on channel ${data.channel}`, 'success');
            form.reset();
            // Clear user-modified tracking since form is reset
            userModifiedColors.clear();
            // Manually populate form from channel 0 (form.reset() doesn't trigger change events)
            populateWriteFormFromChannel(0);
            // Only refresh the specific channel that was written
            setTimeout(() => refreshSingleChannel(data.channel), 1000);
        } else {
            const errorMsg = result.error || 'Unknown error';
            showStatus(`Write failed: ${typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)}`, 'error');
        }
    } catch (error) {
        const errorMsg = error.message || (typeof error === 'string' ? error : JSON.stringify(error));
        showStatus(`Write failed: ${errorMsg}`, 'error');
    }
}

async function handleEraseTag(e) {
    e.preventDefault();
    const form = e.target;
    const formData = new FormData(form);

    if (!formData.get('confirm')) {
        showStatus('Please confirm tag erasure', 'error');
        return;
    }

    const data = {
        channel: parseInt(formData.get('channel')),
        confirm: true
    };

    try {
        showStatus('Erasing tag...', 'info');
        const response = await apiCall('/erase', 'POST', data);
        // Moonraker wraps response in {result: {...}}
        const result = response.result || response;

        if (result.success) {
            const verifyMsg = result.verified ? ' and verified' : '';
            showStatus(`Tag erased${verifyMsg} on channel ${data.channel}`, 'success');
            form.reset();
            // Only refresh the specific channel that was erased
            setTimeout(() => refreshSingleChannel(data.channel), 1000);
        } else {
            const errorMsg = result.error || 'Unknown error';
            showStatus(`Erase failed: ${typeof errorMsg === 'string' ? errorMsg : JSON.stringify(errorMsg)}`, 'error');
        }
    } catch (error) {
        const errorMsg = error.message || (typeof error === 'string' ? error : JSON.stringify(error));
        showStatus(`Erase failed: ${errorMsg}`, 'error');
    }
}

// Button State Management
function updateButtonStates() {
    // Write form
    const writeChannel = parseInt(document.querySelector('#write-form select[name="channel"]').value);
    const writeBtn = document.querySelector('#write-form button[type="submit"]');
    const writeChannelData = channelsData.find(c => c.channel === writeChannel);
    const writeIsM1 = writeChannelData?.tag_type === 'M1';

    writeBtn.disabled = writeIsM1;

    // Show/hide M1 warning for write form
    let writeWarning = document.getElementById('write-m1-warning');
    if (!writeWarning) {
        writeWarning = document.createElement('div');
        writeWarning.id = 'write-m1-warning';
        writeWarning.className = 'm1-warning';
        writeWarning.textContent = 'M1 (Snapmaker) tags are read-only. Use an NTAG tag instead.';
        writeBtn.parentNode.appendChild(writeWarning);
    }
    writeWarning.style.display = writeIsM1 ? 'block' : 'none';

    // Erase form
    const eraseChannel = parseInt(document.querySelector('#erase-form select[name="channel"]').value);
    const eraseBtn = document.querySelector('#erase-form button[type="submit"]');
    const eraseChannelData = channelsData.find(c => c.channel === eraseChannel);
    const eraseIsM1 = eraseChannelData?.tag_type === 'M1';

    eraseBtn.disabled = eraseIsM1;

    // Show/hide M1 warning for erase form
    let eraseWarning = document.getElementById('erase-m1-warning');
    if (!eraseWarning) {
        eraseWarning = document.createElement('div');
        eraseWarning.id = 'erase-m1-warning';
        eraseWarning.className = 'm1-warning';
        eraseWarning.textContent = 'M1 (Snapmaker) tags are read-only and cannot be erased.';
        eraseBtn.parentNode.appendChild(eraseWarning);
    }
    eraseWarning.style.display = eraseIsM1 ? 'block' : 'none';
}

// Status Messages
let statusTimeout = null;
function showStatus(message, type = 'info') {
    const statusEl = document.getElementById('status-message');

    // Clear any existing timeout
    if (statusTimeout) {
        clearTimeout(statusTimeout);
        statusTimeout = null;
    }

    // Remove show class to reset animation
    statusEl.classList.remove('show');

    // Force reflow to restart animation
    void statusEl.offsetWidth;

    // Set new message and show
    statusEl.textContent = message;
    statusEl.className = `status-message ${type} show`;

    // Set new timeout
    statusTimeout = setTimeout(() => {
        statusEl.classList.remove('show');
        statusTimeout = null;
    }, 4000);
}
