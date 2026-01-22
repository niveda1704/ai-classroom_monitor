/**
 * Middleware Index
 * Export all middleware modules
 */

const { protect, restrictTo, optionalAuth, generateToken, verifyWebSocketToken } = require('./auth');
const { APIError, asyncHandler, notFound, errorHandler } = require('./errorHandler');
const validation = require('./validation');

module.exports = {
    // Auth middleware
    protect,
    restrictTo,
    optionalAuth,
    generateToken,
    verifyWebSocketToken,
    
    // Error handling
    APIError,
    asyncHandler,
    notFound,
    errorHandler,
    
    // Validation
    validation
};
