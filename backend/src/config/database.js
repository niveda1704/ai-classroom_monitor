/**
 * MongoDB Connection Manager
 * Handles database connection with reconnection logic
 */

const mongoose = require('mongoose');
const config = require('./index');
const logger = require('../utils/logger');

let isConnected = false;

const connectDB = async () => {
    if (isConnected) {
        logger.info('Using existing MongoDB connection');
        return;
    }

    try {
        const conn = await mongoose.connect(config.mongodb.uri, config.mongodb.options);
        
        isConnected = true;
        logger.info(`MongoDB Connected: ${conn.connection.host}`);

        // Connection event handlers
        mongoose.connection.on('error', (err) => {
            logger.error('MongoDB connection error:', err);
            isConnected = false;
        });

        mongoose.connection.on('disconnected', () => {
            logger.warn('MongoDB disconnected. Attempting to reconnect...');
            isConnected = false;
        });

        mongoose.connection.on('reconnected', () => {
            logger.info('MongoDB reconnected');
            isConnected = true;
        });

        // Graceful shutdown
        process.on('SIGINT', async () => {
            await mongoose.connection.close();
            logger.info('MongoDB connection closed through app termination');
            process.exit(0);
        });

    } catch (error) {
        logger.error('MongoDB connection failed:', error);
        process.exit(1);
    }
};

const getConnectionStatus = () => ({
    isConnected,
    readyState: mongoose.connection.readyState,
    host: mongoose.connection.host
});

module.exports = { connectDB, getConnectionStatus };
