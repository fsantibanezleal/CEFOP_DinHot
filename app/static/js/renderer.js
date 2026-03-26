/**
 * Dual-canvas renderer for CEFOP DinHot.
 *
 * Manages two HTML5 canvases:
 *   1. Trap canvas (left): Shows trap positions as colored circles
 *   2. Phase mask canvas (right): Shows the computed hologram as grayscale
 *
 * Also renders the convergence error graph in the bottom panel.
 *
 * This replaces the OpenGL-based rendering from the original C++ code:
 *   - GL_Trampas: Rendered trap positions as circles (now trapCanvas)
 *   - GL_Mascaras: Rendered the phase mask as a grayscale texture (now maskCanvas)
 */

class DinHotRenderer {
    /**
     * @param {HTMLCanvasElement} trapCanvas - Canvas for trap position display
     * @param {HTMLCanvasElement} maskCanvas - Canvas for phase mask display
     * @param {HTMLCanvasElement} convCanvas - Canvas for convergence graph
     */
    constructor(trapCanvas, maskCanvas, convCanvas) {
        this.trapCanvas = trapCanvas;
        this.maskCanvas = maskCanvas;
        this.convCanvas = convCanvas;

        this.trapCtx = trapCanvas.getContext('2d');
        this.maskCtx = maskCanvas.getContext('2d');
        this.convCtx = convCanvas.getContext('2d');

        // Colors
        this.colors = {
            background: '#0a0e14',
            grid: '#1a2030',
            gridMajor: '#222a3a',
            trap: '#e8863a',
            trapSelected: '#58a6ff',
            trapGlow: 'rgba(232, 134, 58, 0.3)',
            crosshair: '#30363d',
            text: '#8b949e',
            convergeLine: '#e8863a',
            convergeArea: 'rgba(232, 134, 58, 0.15)',
            convergedDot: '#3fb950',
        };

        // State
        this.traps = [];
        this.phaseMask = null;
        this.maskWidth = 0;
        this.maskHeight = 0;
        this.errorHistory = [];
        this.converged = false;
        this.iterations = 0;

        // Cached ImageData for phase mask
        this._maskImageData = null;

        this._resizeCanvases();
        window.addEventListener('resize', () => this._resizeCanvases());
    }

    /**
     * Resize canvases to match their CSS display size.
     * @private
     */
    _resizeCanvases() {
        for (const canvas of [this.trapCanvas, this.maskCanvas]) {
            const rect = canvas.getBoundingClientRect();
            const dpr = window.devicePixelRatio || 1;
            canvas.width = rect.width * dpr;
            canvas.height = rect.height * dpr;
            canvas.getContext('2d').setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        // Convergence canvas
        const convRect = this.convCanvas.getBoundingClientRect();
        const dpr = window.devicePixelRatio || 1;
        this.convCanvas.width = convRect.width * dpr;
        this.convCanvas.height = convRect.height * dpr;
        this.convCtx.setTransform(dpr, 0, 0, dpr, 0, 0);
    }

    /**
     * Update the renderer with new simulation state.
     * @param {object} state - State from the server
     */
    update(state) {
        if (!state) return;

        if (state.traps) {
            this.traps = state.traps;
        }
        if (state.phase_mask) {
            this.phaseMask = state.phase_mask;
            this.maskWidth = state.mask_width;
            this.maskHeight = state.mask_height;
            this._maskImageData = null; // invalidate cache
        }
        if (state.error_history) {
            this.errorHistory = state.error_history;
        }
        if (state.converged !== undefined) {
            this.converged = state.converged;
        }
        if (state.iterations !== undefined) {
            this.iterations = state.iterations;
        }

        this.render();
    }

    /**
     * Render all three canvases.
     */
    render() {
        this._renderTraps();
        this._renderPhaseMask();
        this._renderConvergence();
    }

    /**
     * Render trap positions on the left canvas.
     *
     * Draws:
     * - Background grid (subtle lines at regular intervals)
     * - Crosshair axes
     * - Each trap as a glowing circle with position label
     *
     * @private
     */
    _renderTraps() {
        const ctx = this.trapCtx;
        const w = this.trapCanvas.getBoundingClientRect().width;
        const h = this.trapCanvas.getBoundingClientRect().height;

        // Clear
        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        // Grid
        const gridSize = w / 10;
        ctx.strokeStyle = this.colors.grid;
        ctx.lineWidth = 0.5;
        for (let i = 0; i <= 10; i++) {
            const x = i * gridSize;
            const y = i * (h / 10);
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, h);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(w, y);
            ctx.stroke();
        }

        // Center crosshair
        ctx.strokeStyle = this.colors.gridMajor;
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(w / 2, 0);
        ctx.lineTo(w / 2, h);
        ctx.stroke();
        ctx.beginPath();
        ctx.moveTo(0, h / 2);
        ctx.lineTo(w, h / 2);
        ctx.stroke();

        // Draw traps
        for (let i = 0; i < this.traps.length; i++) {
            const trap = this.traps[i];
            // Convert normalized [-1,1] to canvas pixels
            const cx = (trap.x + 1) / 2 * w;
            const cy = (1 - (trap.y + 1) / 2) * h; // flip Y

            // Glow
            const gradient = ctx.createRadialGradient(cx, cy, 0, cx, cy, 18);
            gradient.addColorStop(0, this.colors.trapGlow);
            gradient.addColorStop(1, 'transparent');
            ctx.fillStyle = gradient;
            ctx.fillRect(cx - 18, cy - 18, 36, 36);

            // Circle
            ctx.beginPath();
            ctx.arc(cx, cy, 6, 0, Math.PI * 2);
            ctx.fillStyle = this.colors.trap;
            ctx.fill();
            ctx.strokeStyle = '#fff';
            ctx.lineWidth = 1.5;
            ctx.stroke();

            // Label
            ctx.fillStyle = this.colors.text;
            ctx.font = '10px Consolas, monospace';
            ctx.textAlign = 'left';
            ctx.fillText(
                `T${i} (${trap.x.toFixed(2)}, ${trap.y.toFixed(2)})`,
                cx + 10, cy + 3
            );
        }

        // "No traps" hint
        if (this.traps.length === 0) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '13px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Click to add traps', w / 2, h / 2);
        }
    }

    /**
     * Render the phase mask on the right canvas.
     *
     * Converts the 2D array of phase values (0-255) into a grayscale
     * image using ImageData. This replaces the OpenGL texture rendering
     * from GL_Mascaras::Renderizar in the original C++ code.
     *
     * @private
     */
    _renderPhaseMask() {
        const ctx = this.maskCtx;
        const w = this.maskCanvas.getBoundingClientRect().width;
        const h = this.maskCanvas.getBoundingClientRect().height;

        // Clear
        ctx.fillStyle = this.colors.background;
        ctx.fillRect(0, 0, w, h);

        if (!this.phaseMask || this.phaseMask.length === 0) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '13px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Phase mask will appear here', w / 2, h / 2);
            return;
        }

        // Build ImageData from phase mask array
        const mh = this.maskHeight;
        const mw = this.maskWidth;

        // Create an offscreen canvas at the mask resolution
        const offscreen = document.createElement('canvas');
        offscreen.width = mw;
        offscreen.height = mh;
        const offCtx = offscreen.getContext('2d');
        const imgData = offCtx.createImageData(mw, mh);
        const data = imgData.data;

        for (let row = 0; row < mh; row++) {
            for (let col = 0; col < mw; col++) {
                const val = this.phaseMask[row][col];
                const idx = (row * mw + col) * 4;
                data[idx] = val;       // R
                data[idx + 1] = val;   // G
                data[idx + 2] = val;   // B
                data[idx + 3] = 255;   // A
            }
        }

        offCtx.putImageData(imgData, 0, 0);

        // Scale to canvas size with nearest-neighbor for crisp pixels
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(offscreen, 0, 0, w, h);

        // Draw trap positions as small markers on the phase mask too
        for (let i = 0; i < this.traps.length; i++) {
            const trap = this.traps[i];
            const cx = (trap.x + 1) / 2 * w;
            const cy = (1 - (trap.y + 1) / 2) * h;

            ctx.beginPath();
            ctx.arc(cx, cy, 3, 0, Math.PI * 2);
            ctx.strokeStyle = this.colors.trap;
            ctx.lineWidth = 1.5;
            ctx.stroke();
        }
    }

    /**
     * Render the convergence error graph.
     *
     * Shows the error history as a line chart, with the most recent
     * value highlighted. A green dot indicates convergence.
     *
     * @private
     */
    _renderConvergence() {
        const ctx = this.convCtx;
        const rect = this.convCanvas.getBoundingClientRect();
        const w = rect.width;
        const h = rect.height;

        // Clear
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, w, h);

        if (this.errorHistory.length < 2) {
            ctx.fillStyle = this.colors.text;
            ctx.font = '10px sans-serif';
            ctx.textAlign = 'center';
            ctx.fillText('Error convergence', w / 2, h / 2);
            return;
        }

        const data = this.errorHistory;
        const maxVal = Math.max(...data) || 1;
        const minVal = Math.min(...data);
        const range = (maxVal - minVal) || 1;
        const padding = { top: 8, right: 8, bottom: 16, left: 8 };
        const plotW = w - padding.left - padding.right;
        const plotH = h - padding.top - padding.bottom;

        // Fill area under curve
        ctx.beginPath();
        ctx.moveTo(padding.left, padding.top + plotH);
        for (let i = 0; i < data.length; i++) {
            const x = padding.left + (i / (data.length - 1)) * plotW;
            const y = padding.top + (1 - (data[i] - minVal) / range) * plotH;
            ctx.lineTo(x, y);
        }
        ctx.lineTo(padding.left + plotW, padding.top + plotH);
        ctx.closePath();
        ctx.fillStyle = this.colors.convergeArea;
        ctx.fill();

        // Line
        ctx.beginPath();
        for (let i = 0; i < data.length; i++) {
            const x = padding.left + (i / (data.length - 1)) * plotW;
            const y = padding.top + (1 - (data[i] - minVal) / range) * plotH;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.strokeStyle = this.colors.convergeLine;
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Current value dot
        const lastX = padding.left + plotW;
        const lastY = padding.top + (1 - (data[data.length - 1] - minVal) / range) * plotH;
        ctx.beginPath();
        ctx.arc(lastX, lastY, 3, 0, Math.PI * 2);
        ctx.fillStyle = this.converged ? this.colors.convergedDot : this.colors.convergeLine;
        ctx.fill();

        // Labels
        ctx.fillStyle = this.colors.text;
        ctx.font = '9px Consolas, monospace';
        ctx.textAlign = 'left';
        ctx.fillText(`err: ${data[data.length - 1].toExponential(2)}`, padding.left, h - 2);
        ctx.textAlign = 'right';
        ctx.fillText(
            this.converged ? 'CONVERGED' : `iter: ${this.iterations}`,
            w - padding.right, h - 2
        );
    }

    /**
     * Convert canvas pixel coordinates to normalized [-1, 1] coordinates.
     * @param {HTMLCanvasElement} canvas
     * @param {number} clientX - Mouse clientX
     * @param {number} clientY - Mouse clientY
     * @returns {{x: number, y: number}} Normalized coordinates
     */
    canvasToNormalized(canvas, clientX, clientY) {
        const rect = canvas.getBoundingClientRect();
        const px = (clientX - rect.left) / rect.width;
        const py = (clientY - rect.top) / rect.height;
        return {
            x: px * 2 - 1,              // [0,1] -> [-1,1]
            y: -(py * 2 - 1),           // [0,1] -> [1,-1] (flip Y)
        };
    }
}
