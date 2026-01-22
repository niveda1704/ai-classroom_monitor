/**
 * Main Server Entry Point
 * AI-Powered Classroom Analytics Backend
 */

const express = require('express');
const http = require('http');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
const path = require('path');

const config = require('./config');
const { connectDB } = require('./config/database');
const logger = require('./utils/logger');
const { notFound, errorHandler } = require('./middleware');
const wsManager = require('./services/websocket');

// Import routes
const { authRoutes, studentRoutes, sessionRoutes, eventRoutes } = require('./routes');

// Initialize Express app
const app = express();

// Create HTTP server for WebSocket support
const server = http.createServer(app);

// ===== Security Middleware =====

// Helmet for security headers
app.use(helmet({
    crossOriginResourcePolicy: { policy: 'cross-origin' }
}));

// CORS configuration
app.use(cors({
    origin: config.cors.origin,
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization']
}));

// Rate limiting - DISABLED for local development
// const limiter = rateLimit({
//     windowMs: config.rateLimit.windowMs,
//     max: config.rateLimit.max,
//     message: {
//         success: false,
//         error: 'Too many requests, please try again later'
//     }
// });
// app.use('/api/', limiter);

// ===== Body Parsers =====

// JSON body parser with size limit for base64 images
app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ extended: true, limit: '50mb' }));

// ===== Request Logging =====

app.use((req, res, next) => {
    const start = Date.now();
    
    res.on('finish', () => {
        const duration = Date.now() - start;
        logger.debug(`${req.method} ${req.originalUrl} ${res.statusCode} ${duration}ms`);
    });
    
    next();
});

// ===== Static Files =====

// Serve static files (for snippets, thumbnails, etc.)
app.use('/static', express.static(path.join(__dirname, '../static')));
app.use('/snippets', express.static(path.join(__dirname, '../snippets')));

// ===== API Routes =====

app.use('/api/auth', authRoutes);
app.use('/api/students', studentRoutes);
app.use('/api/sessions', sessionRoutes);
app.use('/api/events', eventRoutes);

// ===== Health Check =====

app.get('/health', (req, res) => {
    res.json({
        success: true,
        status: 'healthy',
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
        websocket: wsManager.getStats()
    });
});

// ===== API Documentation Endpoint =====

app.get('/api', (req, res) => {
    res.json({
        success: true,
        message: 'Classroom Analytics API',
        version: '1.0.0',
        endpoints: {
            auth: {
                'POST /api/auth/register': 'Register new user',
                'POST /api/auth/login': 'Login and get token',
                'GET /api/auth/me': 'Get current user profile',
                'PUT /api/auth/password': 'Change password',
                'PUT /api/auth/profile': 'Update profile'
            },
            students: {
                'POST /api/students': 'Create new student',
                'GET /api/students': 'List students',
                'GET /api/students/:id': 'Get student details',
                'PUT /api/students/:id': 'Update student',
                'DELETE /api/students/:id': 'Delete student',
                'POST /api/students/:id/enrollment/start': 'Start enrollment',
                'POST /api/students/:id/enrollment/capture': 'Capture face image',
                'POST /api/students/:id/enrollment/complete': 'Complete enrollment'
            },
            sessions: {
                'POST /api/sessions': 'Create session',
                'GET /api/sessions': 'List sessions',
                'GET /api/sessions/:id': 'Get session details',
                'POST /api/sessions/:id/start': 'Start session',
                'POST /api/sessions/:id/pause': 'Pause session',
                'POST /api/sessions/:id/resume': 'Resume session',
                'POST /api/sessions/:id/complete': 'Complete session',
                'GET /api/sessions/:id/analytics': 'Get analytics',
                'GET /api/sessions/:id/report': 'Download report'
            },
            events: {
                'POST /api/events': 'Create event',
                'POST /api/events/batch': 'Create batch events',
                'GET /api/events/:id': 'Get event',
                'GET /api/events/session/:id/summary': 'Get session event summary',
                'GET /api/events/session/:id/timeline': 'Get event timeline'
            },
            websocket: {
                'WS /ws?token=<JWT>': 'Real-time updates connection'
            }
        }
    });
});

// ===== Error Handling =====

app.use(notFound);
app.use(errorHandler);

// ===== Server Startup =====

const startServer = async () => {
    try {
        // Skip MongoDB connection - using in-memory store
        // await connectDB();
        logger.info('Using in-memory data store (MongoDB disabled)');

        // Initialize WebSocket server
        wsManager.initialize(server);

        // Start HTTP server
        server.listen(config.port, () => {
            logger.info(`
╔════════════════════════════════════════════════════════════╗
║       AI Classroom Analytics Backend Server                ║
╠════════════════════════════════════════════════════════════╣
║  🚀 Server running on port ${config.port}                          ║
║  📡 WebSocket available at ws://localhost:${config.port}/ws        ║
║  🔧 Environment: ${config.nodeEnv.padEnd(15)}                       ║
║  📊 API Docs: http://localhost:${config.port}/api                  ║
║  💾 Storage: In-Memory (demo mode)                         ║
╚════════════════════════════════════════════════════════════╝
            `);
        });

    } catch (error) {
        logger.error('Failed to start server:', error);
        process.exit(1);
    }
};

// ===== Graceful Shutdown =====

const shutdown = async (signal) => {
    logger.info(`\n${signal} received. Shutting down gracefully...`);
    
    // Close WebSocket connections
    wsManager.shutdown();
    
    // Close HTTP server
    server.close(() => {
        logger.info('HTTP server closed');
        process.exit(0);
    });

    // Force close after 10 seconds
    setTimeout(() => {
        logger.error('Could not close connections in time, forcefully shutting down');
        process.exit(1);
    }, 10000);
};

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

// Handle unhandled promise rejections
process.on('unhandledRejection', (err) => {
    logger.error('Unhandled Promise Rejection:', err);
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
    logger.error('Uncaught Exception:', err);
    process.exit(1);
});

// Start the server
startServer();

module.exports = { app, server };
