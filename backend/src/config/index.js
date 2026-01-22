/**
 * Application Configuration
 * Centralizes all environment variables and configuration settings
 */

require('dotenv').config();

const config = {
    // Server settings
    port: parseInt(process.env.PORT, 10) || 3001,
    nodeEnv: process.env.NODE_ENV || 'development',
    
    // MongoDB settings
    mongodb: {
        uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/classroom_analytics',
        options: {
            maxPoolSize: 10,
            serverSelectionTimeoutMS: 5000,
            socketTimeoutMS: 45000,
        }
    },
    
    // JWT settings
    jwt: {
        secret: process.env.JWT_SECRET || 'default-secret-change-me',
        expiresIn: process.env.JWT_EXPIRES_IN || '24h'
    },
    
    // AI Service settings
    aiService: {
        url: process.env.AI_SERVICE_URL || 'http://localhost:8000',
        timeout: 30000
    },
    
    // Session settings
    session: {
        snippetDuration: parseInt(process.env.SESSION_SNIPPET_DURATION_SECONDS, 10) || 10,
        maxSnippetSize: parseInt(process.env.MAX_SNIPPET_SIZE_MB, 10) || 50
    },
    
    // CORS settings
    cors: {
        origin: process.env.CORS_ORIGIN || 'http://localhost:3000',
        credentials: true
    },
    
    // Rate limiting
    rateLimit: {
        windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS, 10) || 900000,
        max: parseInt(process.env.RATE_LIMIT_MAX_REQUESTS, 10) || 100
    }
};

// Validate critical configurations
if (config.nodeEnv === 'production' && config.jwt.secret === 'default-secret-change-me') {
    console.error('⚠️  WARNING: Using default JWT secret in production!');
}

module.exports = config;
