/**
 * Error Handler Middleware
 * Centralized error handling with proper responses
 */

const logger = require('../utils/logger');

/**
 * Custom API Error class
 */
class APIError extends Error {
    constructor(message, statusCode, code = null) {
        super(message);
        this.statusCode = statusCode;
        this.code = code;
        this.isOperational = true;
        Error.captureStackTrace(this, this.constructor);
    }
}

/**
 * Async handler wrapper to catch errors in async routes
 */
const asyncHandler = (fn) => (req, res, next) => {
    Promise.resolve(fn(req, res, next)).catch(next);
};

/**
 * Not found handler
 */
const notFound = (req, res, next) => {
    const error = new APIError(`Route not found: ${req.originalUrl}`, 404, 'ROUTE_NOT_FOUND');
    next(error);
};

/**
 * Global error handler
 */
const errorHandler = (err, req, res, next) => {
    let error = { ...err };
    error.message = err.message;

    // Log error
    logger.error('Error:', {
        message: err.message,
        stack: err.stack,
        url: req.originalUrl,
        method: req.method
    });

    // Mongoose bad ObjectId
    if (err.name === 'CastError') {
        const message = 'Resource not found';
        error = new APIError(message, 404, 'INVALID_ID');
    }

    // Mongoose duplicate key
    if (err.code === 11000) {
        const field = Object.keys(err.keyValue)[0];
        const message = `Duplicate value for field: ${field}`;
        error = new APIError(message, 400, 'DUPLICATE_FIELD');
    }

    // Mongoose validation error
    if (err.name === 'ValidationError') {
        const messages = Object.values(err.errors).map(e => e.message);
        error = new APIError(messages.join(', '), 400, 'VALIDATION_ERROR');
    }

    // JWT errors
    if (err.name === 'JsonWebTokenError') {
        error = new APIError('Invalid token', 401, 'INVALID_TOKEN');
    }

    if (err.name === 'TokenExpiredError') {
        error = new APIError('Token expired', 401, 'TOKEN_EXPIRED');
    }

    // Default error response
    const statusCode = error.statusCode || 500;
    const response = {
        success: false,
        error: error.message || 'Server Error',
        code: error.code || 'SERVER_ERROR'
    };

    // Add stack trace in development
    if (process.env.NODE_ENV === 'development') {
        response.stack = err.stack;
    }

    res.status(statusCode).json(response);
};

module.exports = {
    APIError,
    asyncHandler,
    notFound,
    errorHandler
};
