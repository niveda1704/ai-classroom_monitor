/**
 * Authentication Middleware
 * JWT validation and role-based access control
 */

const jwt = require('jsonwebtoken');
const config = require('../config');
const { User } = require('../models');
const logger = require('../utils/logger');

/**
 * Protect routes - verify JWT token
 */
const protect = async (req, res, next) => {
    try {
        let token;

        // Check for token in Authorization header
        if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
            token = req.headers.authorization.split(' ')[1];
        }

        if (!token) {
            return res.status(401).json({
                success: false,
                error: 'Not authorized - no token provided'
            });
        }

        // Verify token
        let decoded;
        try {
            decoded = jwt.verify(token, config.jwt.secret);
        } catch (err) {
            if (err.name === 'TokenExpiredError') {
                return res.status(401).json({
                    success: false,
                    error: 'Token expired'
                });
            }
            return res.status(401).json({
                success: false,
                error: 'Invalid token'
            });
        }

        // Check if user still exists
        const user = await User.findById(decoded.id).select('+password');
        if (!user) {
            return res.status(401).json({
                success: false,
                error: 'User no longer exists'
            });
        }

        // Check if user is still active
        if (!user.isActive) {
            return res.status(401).json({
                success: false,
                error: 'User account is deactivated'
            });
        }

        // Check if user changed password after token was issued
        if (user.changedPasswordAfter(decoded.iat)) {
            return res.status(401).json({
                success: false,
                error: 'Password recently changed. Please log in again.'
            });
        }

        // Attach user to request
        req.user = user;
        next();
    } catch (error) {
        logger.error('Auth middleware error:', error);
        return res.status(500).json({
            success: false,
            error: 'Authentication error'
        });
    }
};

/**
 * Restrict to specific roles
 */
const restrictTo = (...roles) => {
    return (req, res, next) => {
        if (!roles.includes(req.user.role)) {
            return res.status(403).json({
                success: false,
                error: 'You do not have permission to perform this action'
            });
        }
        next();
    };
};

/**
 * Optional authentication - attach user if token exists but don't require it
 */
const optionalAuth = async (req, res, next) => {
    try {
        let token;

        if (req.headers.authorization && req.headers.authorization.startsWith('Bearer')) {
            token = req.headers.authorization.split(' ')[1];
        }

        if (token) {
            try {
                const decoded = jwt.verify(token, config.jwt.secret);
                const user = await User.findById(decoded.id);
                if (user && user.isActive) {
                    req.user = user;
                }
            } catch (err) {
                // Token invalid - continue without user
            }
        }

        next();
    } catch (error) {
        next();
    }
};

/**
 * Generate JWT token
 */
const generateToken = (user) => {
    return jwt.sign(
        { id: user._id, role: user.role },
        config.jwt.secret,
        { expiresIn: config.jwt.expiresIn }
    );
};

/**
 * Verify WebSocket connection token
 */
const verifyWebSocketToken = async (token) => {
    try {
        const decoded = jwt.verify(token, config.jwt.secret);
        const user = await User.findById(decoded.id);
        
        if (!user || !user.isActive) {
            return null;
        }
        
        return user;
    } catch (error) {
        return null;
    }
};

module.exports = {
    protect,
    restrictTo,
    optionalAuth,
    generateToken,
    verifyWebSocketToken
};
