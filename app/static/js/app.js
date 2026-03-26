/**
 * Main application orchestrator for CEFOP DinHot.
 *
 * Initializes and coordinates all components:
 *   - WebSocket client for server communication
 *   - Renderer for dual-canvas visualization
 *   - Controls for mode selection and parameters
 *   - Mouse event handling on the trap canvas
 *
 * Application lifecycle:
 *   1. Page load -> create components
 *   2. Init button -> POST /api/init, then connect WebSocket
 *   3. User interacts via mouse on trap canvas
 *   4. Events sent to server via WebSocket
 *   5. Server responds with updated state
 *   6. Renderer updates both canvases
 */

// Application state
let ws = null;
let renderer = null;
let controls = null;
let isDragging = false;
let initialized = false;

/**
 * Initialize the application when the DOM is ready.
 */
document.addEventListener('DOMContentLoaded', () => {
    // Create renderer
    const trapCanvas = document.getElementById('trap-canvas');
    const maskCanvas = document.getElementById('mask-canvas');
    const convCanvas = document.getElementById('convergence-canvas');
    renderer = new DinHotRenderer(trapCanvas, maskCanvas, convCanvas);

    // Create controls
    controls = new DinHotControls(
        handleModeChange,
        handleInit,
        handleRecalculate,
        handleClearAll
    );

    // Bind mouse events on the trap canvas
    bindCanvasEvents(trapCanvas);

    // Render initial empty state
    renderer.render();

    // Auto-initialize on page load
    handleInit({
        resolution_x: 512,
        resolution_y: 512,
        wavelength_nm: 632.0,
        max_iterations: 50,
        tolerance: 1e-6,
    });
});

/**
 * Handle initialization request.
 * @param {object} config - Configuration parameters
 */
async function handleInit(config) {
    try {
        const response = await fetch('/api/init', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config),
        });
        const result = await response.json();

        if (result.status === 'initialized') {
            initialized = true;
            connectWebSocket();
        }
    } catch (e) {
        console.error('Init failed:', e);
    }
}

/**
 * Connect (or reconnect) the WebSocket.
 */
function connectWebSocket() {
    if (ws) {
        ws.disconnect();
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws`;

    ws = new DinHotWebSocket(url, handleServerMessage, handleConnectionStatus);
    ws.connect();
}

/**
 * Handle incoming message from the server.
 * @param {object} data - Parsed JSON message
 */
function handleServerMessage(data) {
    if (data.state) {
        renderer.update(data.state);
        controls.updateInfo(data.state);
    }

    if (data.error) {
        console.error('Server error:', data.error);
    }
}

/**
 * Handle WebSocket connection status change.
 * @param {boolean} connected
 */
function handleConnectionStatus(connected) {
    controls.updateConnectionStatus(connected);
}

/**
 * Handle interaction mode change.
 * @param {string} mode - "create", "move", or "delete"
 */
function handleModeChange(mode) {
    if (ws) {
        ws.sendMode(mode);
    }
    // Update cursor style
    const trapCanvas = document.getElementById('trap-canvas');
    if (mode === 'delete') {
        trapCanvas.style.cursor = 'not-allowed';
    } else if (mode === 'move') {
        trapCanvas.style.cursor = 'grab';
    } else {
        trapCanvas.style.cursor = 'crosshair';
    }
}

/**
 * Handle recalculate button.
 */
function handleRecalculate() {
    if (ws) {
        ws.sendRecalculate();
    }
}

/**
 * Handle clear all button.
 * Reinitializes the simulation with current parameters.
 */
async function handleClearAll() {
    const config = {
        resolution_x: parseInt(document.getElementById('param-res-x').value) || 512,
        resolution_y: parseInt(document.getElementById('param-res-y').value) || 512,
        wavelength_nm: parseFloat(document.getElementById('param-wavelength').value) || 632.0,
        max_iterations: parseInt(document.getElementById('param-max-iter').value) || 50,
        tolerance: parseFloat(document.getElementById('param-tolerance').value) || 1e-6,
    };
    await handleInit(config);
    // Request fresh state
    if (ws && ws.connected) {
        ws.sendStateRequest();
    }
}

/**
 * Bind mouse events to the trap canvas.
 *
 * Handles:
 *   - mousedown: Send click event (create/delete/select depending on mode)
 *   - mousemove: Send drag event if mouse is down (move mode)
 *   - mouseup: Send release event
 *
 * Coordinates are converted from canvas pixels to normalized [-1, 1].
 *
 * @param {HTMLCanvasElement} canvas
 */
function bindCanvasEvents(canvas) {
    canvas.addEventListener('mousedown', (e) => {
        if (!ws || !initialized) return;
        e.preventDefault();

        const pos = renderer.canvasToNormalized(canvas, e.clientX, e.clientY);
        isDragging = true;
        ws.sendClick(pos.x, pos.y);
    });

    canvas.addEventListener('mousemove', (e) => {
        if (!ws || !isDragging) return;
        e.preventDefault();

        const pos = renderer.canvasToNormalized(canvas, e.clientX, e.clientY);
        ws.sendDrag(pos.x, pos.y);
    });

    canvas.addEventListener('mouseup', (e) => {
        if (!ws || !isDragging) return;
        e.preventDefault();

        isDragging = false;
        ws.sendRelease();
    });

    canvas.addEventListener('mouseleave', (e) => {
        if (isDragging) {
            isDragging = false;
            if (ws) ws.sendRelease();
        }
    });

    // Prevent context menu on right-click
    canvas.addEventListener('contextmenu', (e) => e.preventDefault());
}
