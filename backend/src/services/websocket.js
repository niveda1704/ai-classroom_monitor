/**
 * WebSocket Handler
 * Manages real-time communication for live monitoring
 */

const WebSocket = require('ws');
const { verifyWebSocketToken } = require('../middleware/auth');
const { Session, Event } = require('../models');
const logger = require('../utils/logger');

class WebSocketManager {
    constructor() {
        this.wss = null;
        this.clients = new Map(); // Map of userId -> Set of WebSocket connections
        this.sessionClients = new Map(); // Map of sessionId -> Set of client connections
        this.heartbeatInterval = null;
    }

    /**
     * Initialize WebSocket server
     */
    initialize(server) {
        this.wss = new WebSocket.Server({ 
            server,
            path: '/ws'
        });

        this.wss.on('connection', this.handleConnection.bind(this));

        // Start heartbeat check
        this.heartbeatInterval = setInterval(() => {
            this.wss.clients.forEach((ws) => {
                if (ws.isAlive === false) {
                    logger.debug('Terminating inactive WebSocket connection');
                    return ws.terminate();
                }
                ws.isAlive = false;
                ws.ping();
            });
        }, 30000);

        logger.info('WebSocket server initialized');
    }

    /**
     * Handle new WebSocket connection
     */
    async handleConnection(ws, req) {
        ws.isAlive = true;

        // Extract token from query string
        const url = new URL(req.url, `http://${req.headers.host}`);
        const token = url.searchParams.get('token');

        if (!token) {
            ws.close(4001, 'Authentication required');
            return;
        }

        // Verify token
        const user = await verifyWebSocketToken(token);
        if (!user) {
            ws.close(4002, 'Invalid token');
            return;
        }

        // Store user info on connection
        ws.userId = user._id.toString();
        ws.userName = user.name;
        ws.sessionId = null;

        // Add to clients map
        if (!this.clients.has(ws.userId)) {
            this.clients.set(ws.userId, new Set());
        }
        this.clients.get(ws.userId).add(ws);

        logger.info(`WebSocket connected: ${user.email}`);

        // Send welcome message
        this.sendToClient(ws, {
            type: 'connected',
            message: 'WebSocket connection established',
            userId: ws.userId
        });

        // Handle messages
        ws.on('message', (data) => this.handleMessage(ws, data));

        // Handle pong (heartbeat response)
        ws.on('pong', () => {
            ws.isAlive = true;
        });

        // Handle close
        ws.on('close', () => this.handleClose(ws));

        // Handle errors
        ws.on('error', (error) => {
            logger.error('WebSocket error:', error);
        });
    }

    /**
     * Handle incoming messages
     */
    async handleMessage(ws, data) {
        try {
            const message = JSON.parse(data.toString());

            switch (message.type) {
                case 'subscribe_session':
                    await this.subscribeToSession(ws, message.sessionId);
                    break;

                case 'unsubscribe_session':
                    this.unsubscribeFromSession(ws);
                    break;

                case 'live_metrics':
                    // Forward live metrics to session subscribers
                    await this.handleLiveMetrics(ws, message.data);
                    break;

                case 'ping':
                    this.sendToClient(ws, { type: 'pong', timestamp: Date.now() });
                    break;

                default:
                    logger.warn(`Unknown WebSocket message type: ${message.type}`);
            }
        } catch (error) {
            logger.error('WebSocket message error:', error);
            this.sendToClient(ws, {
                type: 'error',
                message: 'Invalid message format'
            });
        }
    }

    /**
     * Subscribe client to session updates
     */
    async subscribeToSession(ws, sessionId) {
        // Verify session access
        const session = await Session.findOne({
            _id: sessionId,
            faculty: ws.userId
        });

        if (!session) {
            this.sendToClient(ws, {
                type: 'error',
                message: 'Session not found or access denied'
            });
            return;
        }

        // Unsubscribe from previous session if any
        if (ws.sessionId) {
            this.unsubscribeFromSession(ws);
        }

        // Add to session clients
        ws.sessionId = sessionId;
        if (!this.sessionClients.has(sessionId)) {
            this.sessionClients.set(sessionId, new Set());
        }
        this.sessionClients.get(sessionId).add(ws);

        logger.info(`Client ${ws.userId} subscribed to session ${sessionId}`);

        this.sendToClient(ws, {
            type: 'subscribed',
            sessionId,
            sessionStatus: session.status
        });
    }

    /**
     * Unsubscribe client from session
     */
    unsubscribeFromSession(ws) {
        if (ws.sessionId && this.sessionClients.has(ws.sessionId)) {
            this.sessionClients.get(ws.sessionId).delete(ws);
            
            // Clean up empty session sets
            if (this.sessionClients.get(ws.sessionId).size === 0) {
                this.sessionClients.delete(ws.sessionId);
            }

            logger.debug(`Client ${ws.userId} unsubscribed from session ${ws.sessionId}`);
            ws.sessionId = null;
        }
    }

    /**
     * Handle live metrics from AI service
     */
    async handleLiveMetrics(ws, metricsData) {
        if (!ws.sessionId) {
            return;
        }

        // Update session live metrics
        try {
            await Session.findByIdAndUpdate(ws.sessionId, {
                'liveMetrics.currentStudentCount': metricsData.studentCount,
                'liveMetrics.averageAttention': metricsData.averageAttention,
                'liveMetrics.lastUpdateTime': new Date()
            });
        } catch (error) {
            logger.error('Failed to update session metrics:', error);
        }

        // Broadcast to all session subscribers
        this.broadcastToSession(ws.sessionId, {
            type: 'live_metrics',
            sessionId: ws.sessionId,
            data: metricsData,
            timestamp: Date.now()
        });
    }

    /**
     * Handle connection close
     */
    handleClose(ws) {
        // Remove from session clients
        this.unsubscribeFromSession(ws);

        // Remove from user clients
        if (this.clients.has(ws.userId)) {
            this.clients.get(ws.userId).delete(ws);
            
            if (this.clients.get(ws.userId).size === 0) {
                this.clients.delete(ws.userId);
            }
        }

        logger.info(`WebSocket disconnected: ${ws.userId}`);
    }

    /**
     * Send message to specific client
     */
    sendToClient(ws, message) {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
        }
    }

    /**
     * Send message to all connections of a user
     */
    sendToUser(userId, message) {
        const userClients = this.clients.get(userId.toString());
        if (userClients) {
            userClients.forEach((ws) => {
                this.sendToClient(ws, message);
            });
        }
    }

    /**
     * Broadcast message to all session subscribers
     */
    broadcastToSession(sessionId, message) {
        const sessionSubscribers = this.sessionClients.get(sessionId);
        if (sessionSubscribers) {
            sessionSubscribers.forEach((ws) => {
                this.sendToClient(ws, message);
            });
        }
    }

    /**
     * Broadcast event to session subscribers (called from event route)
     */
    broadcastEvent(sessionId, event) {
        this.broadcastToSession(sessionId, {
            type: 'event',
            sessionId,
            event: {
                id: event._id,
                trackId: event.trackId,
                eventType: event.eventType,
                confidence: event.confidence,
                timestamp: event.timestamp,
                data: event.data
            }
        });
    }

    /**
     * Broadcast detection frame data
     */
    broadcastDetectionFrame(sessionId, frameData) {
        this.broadcastToSession(sessionId, {
            type: 'detection_frame',
            sessionId,
            data: frameData,
            timestamp: Date.now()
        });
    }

    /**
     * Notify session status change
     */
    notifySessionStatusChange(sessionId, status) {
        this.broadcastToSession(sessionId, {
            type: 'session_status',
            sessionId,
            status,
            timestamp: Date.now()
        });
    }

    /**
     * Get connection stats
     */
    getStats() {
        return {
            totalConnections: this.wss ? this.wss.clients.size : 0,
            uniqueUsers: this.clients.size,
            activeSessions: this.sessionClients.size
        };
    }

    /**
     * Cleanup on shutdown
     */
    shutdown() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
        }

        if (this.wss) {
            this.wss.clients.forEach((ws) => {
                ws.close(1001, 'Server shutting down');
            });
            this.wss.close();
        }

        logger.info('WebSocket server shut down');
    }
}

// Singleton instance
const wsManager = new WebSocketManager();

module.exports = wsManager;
