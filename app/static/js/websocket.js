/**
 * WebSocket client for CEFOP DinHot.
 *
 * Manages the WebSocket connection to the FastAPI server, handling
 * connection lifecycle, message serialization, and reconnection.
 *
 * Protocol:
 *   Client -> Server: JSON messages with "action" field
 *   Server -> Client: JSON responses with "state" and/or "action" fields
 */

class DinHotWebSocket {
    /**
     * @param {string} url - WebSocket URL (e.g., "ws://localhost:8003/ws")
     * @param {function} onMessage - Callback for incoming messages
     * @param {function} onStatusChange - Callback for connection status changes
     */
    constructor(url, onMessage, onStatusChange) {
        this.url = url;
        this.onMessage = onMessage;
        this.onStatusChange = onStatusChange;
        this.ws = null;
        this.connected = false;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 10000;
        this.reconnectAttempts = 0;
    }

    /**
     * Establish the WebSocket connection.
     */
    connect() {
        try {
            this.ws = new WebSocket(this.url);

            this.ws.onopen = () => {
                this.connected = true;
                this.reconnectAttempts = 0;
                this.reconnectDelay = 1000;
                this.onStatusChange(true);
                console.log('[WS] Connected to', this.url);
            };

            this.ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    this.onMessage(data);
                } catch (e) {
                    console.error('[WS] Failed to parse message:', e);
                }
            };

            this.ws.onclose = (event) => {
                this.connected = false;
                this.onStatusChange(false);
                console.log('[WS] Disconnected, code:', event.code);
                this._scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('[WS] Error:', error);
            };
        } catch (e) {
            console.error('[WS] Connection failed:', e);
            this._scheduleReconnect();
        }
    }

    /**
     * Schedule a reconnection attempt with exponential backoff.
     * @private
     */
    _scheduleReconnect() {
        this.reconnectAttempts++;
        const delay = Math.min(
            this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts),
            this.maxReconnectDelay
        );
        console.log(`[WS] Reconnecting in ${Math.round(delay)}ms...`);
        setTimeout(() => this.connect(), delay);
    }

    /**
     * Send a JSON message to the server.
     * @param {object} msg - Message object (will be JSON-stringified)
     * @returns {boolean} True if the message was sent
     */
    send(msg) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(msg));
            return true;
        }
        console.warn('[WS] Cannot send: not connected');
        return false;
    }

    /**
     * Send a click event.
     * @param {number} x - Normalized X coordinate [-1, 1]
     * @param {number} y - Normalized Y coordinate [-1, 1]
     */
    sendClick(x, y) {
        return this.send({ action: 'click', x, y });
    }

    /**
     * Send a drag event.
     * @param {number} x - Normalized X coordinate [-1, 1]
     * @param {number} y - Normalized Y coordinate [-1, 1]
     */
    sendDrag(x, y) {
        return this.send({ action: 'drag', x, y });
    }

    /**
     * Send a mouse release event.
     */
    sendRelease() {
        return this.send({ action: 'release' });
    }

    /**
     * Send a mode change.
     * @param {string} mode - "create", "move", or "delete"
     */
    sendMode(mode) {
        return this.send({ action: 'mode', mode });
    }

    /**
     * Request recalculation of the phase mask.
     */
    sendRecalculate() {
        return this.send({ action: 'recalculate' });
    }

    /**
     * Request current simulation state.
     */
    sendStateRequest() {
        return this.send({ action: 'state' });
    }

    /**
     * Close the WebSocket connection.
     */
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
