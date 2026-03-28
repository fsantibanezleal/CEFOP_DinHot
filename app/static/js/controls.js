/**
 * Controls manager for CEFOP DinHot.
 *
 * Handles the bottom control bar: mode selector buttons, parameter inputs,
 * action buttons, and the info display panel.
 *
 * Interaction modes (matching the original C++ radio buttons):
 *   - "create": Click adds a new trap (rbCreateMove in C++)
 *   - "move":   Click selects, drag moves (default mode in C++)
 *   - "delete": Click removes nearest trap (rBDelete in C++)
 */

class DinHotControls {
    /**
     * @param {function} onModeChange - Callback(mode) when mode changes
     * @param {function} onInit - Callback(config) when init is requested
     * @param {function} onRecalculate - Callback when recalculate is pressed
     * @param {function} onClearAll - Callback when clear all is pressed
     */
    constructor(onModeChange, onInit, onRecalculate, onClearAll, onAddGrid) {
        this.onModeChange = onModeChange;
        this.onInit = onInit;
        this.onRecalculate = onRecalculate;
        this.onClearAll = onClearAll;
        this.onAddGrid = onAddGrid || function() {};

        this.currentMode = 'create';

        this._bindModeButtons();
        this._bindActionButtons();
        this._bindParamInputs();
    }

    /**
     * Bind mode selector buttons.
     * @private
     */
    _bindModeButtons() {
        const buttons = document.querySelectorAll('.mode-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', () => {
                const mode = btn.dataset.mode;
                this.setMode(mode);
                this.onModeChange(mode);
            });
        });
    }

    /**
     * Bind action buttons (init, recalculate, clear).
     * @private
     */
    _bindActionButtons() {
        const initBtn = document.getElementById('btn-init');
        if (initBtn) {
            initBtn.addEventListener('click', () => {
                const config = this._getConfig();
                this.onInit(config);
            });
        }

        const recalcBtn = document.getElementById('btn-recalculate');
        if (recalcBtn) {
            recalcBtn.addEventListener('click', () => {
                this.onRecalculate();
            });
        }

        const clearBtn = document.getElementById('btn-clear');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.onClearAll();
            });
        }

        const gridBtn = document.getElementById('btn-add-grid');
        if (gridBtn) {
            gridBtn.addEventListener('click', () => {
                const gridConfig = this._getGridConfig();
                this.onAddGrid(gridConfig);
            });
        }
    }

    /**
     * Bind parameter input fields.
     * @private
     */
    _bindParamInputs() {
        // Parameters update on change -- no live binding needed
    }

    /**
     * Get current configuration from input fields.
     * @returns {object} Configuration object
     * @private
     */
    _getConfig() {
        return {
            resolution_x: parseInt(document.getElementById('param-res-x').value) || 512,
            resolution_y: parseInt(document.getElementById('param-res-y').value) || 512,
            wavelength_nm: parseFloat(document.getElementById('param-wavelength').value) || 632.0,
            max_iterations: parseInt(document.getElementById('param-max-iter').value) || 50,
            tolerance: parseFloat(document.getElementById('param-tolerance').value) || 1e-6,
        };
    }

    /**
     * Get grid configuration from input fields.
     * @returns {object} Grid config with rows, cols, spacing, z_planes
     * @private
     */
    _getGridConfig() {
        const zStr = (document.getElementById('grid-z-planes').value || '0').trim();
        const zPlanes = zStr.split(',').map(s => parseFloat(s.trim())).filter(v => !isNaN(v));
        return {
            rows: parseInt(document.getElementById('grid-rows').value) || 2,
            cols: parseInt(document.getElementById('grid-cols').value) || 2,
            spacing: parseFloat(document.getElementById('grid-spacing').value) || 0.3,
            z_planes: zPlanes.length > 0 ? zPlanes : [0.0],
        };
    }

    /**
     * Set the active mode and update button styling.
     * @param {string} mode - "create", "move", or "delete"
     */
    setMode(mode) {
        this.currentMode = mode;
        const buttons = document.querySelectorAll('.mode-btn');
        buttons.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
    }

    /**
     * Update the info display with current state.
     * @param {object} state - Simulation state from server
     */
    updateInfo(state) {
        if (!state) return;

        const setVal = (id, val) => {
            const el = document.getElementById(id);
            if (el) el.textContent = val;
        };

        setVal('info-num-traps', state.traps ? state.traps.length : 0);
        setVal('info-iterations', state.iterations || 0);
        setVal('info-converged', state.converged ? 'Yes' : 'No');

        if (state.error_history && state.error_history.length > 0) {
            const lastErr = state.error_history[state.error_history.length - 1];
            setVal('info-error', lastErr.toExponential(3));
        } else {
            setVal('info-error', '--');
        }

        // Update trap list table
        this._updateTrapList(state.traps || []);
    }

    /**
     * Update the trap list table.
     * @param {Array} traps - Array of trap objects
     * @private
     */
    _updateTrapList(traps) {
        const tbody = document.getElementById('trap-list-body');
        if (!tbody) return;

        tbody.innerHTML = '';
        traps.forEach((trap, i) => {
            const row = document.createElement('tr');
            const zVal = (trap.z !== undefined && trap.z !== null) ? trap.z.toFixed(2) : '0.00';
            row.innerHTML = `
                <td>${i}</td>
                <td>${trap.x.toFixed(3)}</td>
                <td>${trap.y.toFixed(3)}</td>
                <td>${zVal}</td>
                <td>${trap.intensity.toExponential(2)}</td>
            `;
            tbody.appendChild(row);
        });
    }

    /**
     * Update connection status indicator.
     * @param {boolean} connected
     */
    updateConnectionStatus(connected) {
        const dot = document.getElementById('status-dot');
        if (dot) {
            dot.classList.toggle('connected', connected);
        }
        const text = document.getElementById('status-text');
        if (text) {
            text.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }
}
