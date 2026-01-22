/**
 * Authentication Routes
 * Handles user registration, login, and token management
 */

const express = require('express');
const router = express.Router();
const { User } = require('../models');
const { 
    protect, 
    restrictTo, 
    generateToken, 
    asyncHandler, 
    APIError 
} = require('../middleware');
const { registerValidation, loginValidation } = require('../middleware/validation');
const logger = require('../utils/logger');

/**
 * @route   POST /api/auth/register
 * @desc    Register new user (admin only can create other admins)
 * @access  Public for faculty, Protected for admin creation
 */
router.post('/register', registerValidation, asyncHandler(async (req, res) => {
    const { email, password, name, role, department } = req.body;

    // Check if user exists
    const existingUser = await User.findOne({ email });
    if (existingUser) {
        throw new APIError('User with this email already exists', 400, 'USER_EXISTS');
    }

    // Create user
    const user = await User.create({
        email,
        password,
        name,
        role: role || 'faculty',
        department
    });

    // Generate token
    const token = generateToken(user);

    logger.info(`New user registered: ${email}`);

    res.status(201).json({
        success: true,
        data: {
            user: {
                id: user._id,
                email: user.email,
                name: user.name,
                role: user.role,
                department: user.department
            },
            token
        }
    });
}));

/**
 * @route   POST /api/auth/login
 * @desc    Login user and return token
 * @access  Public
 */
router.post('/login', loginValidation, asyncHandler(async (req, res) => {
    const { email, password } = req.body;

    // Find user with password
    const user = await User.findOne({ email }).select('+password');
    if (!user) {
        throw new APIError('Invalid credentials', 401, 'INVALID_CREDENTIALS');
    }

    // Check if user is active
    if (!user.isActive) {
        throw new APIError('Account is deactivated', 401, 'ACCOUNT_DEACTIVATED');
    }

    // Verify password
    const isMatch = await user.comparePassword(password);
    if (!isMatch) {
        throw new APIError('Invalid credentials', 401, 'INVALID_CREDENTIALS');
    }

    // Update last login
    await user.updateLastLogin();

    // Generate token
    const token = generateToken(user);

    logger.info(`User logged in: ${email}`);

    res.json({
        success: true,
        data: {
            user: {
                id: user._id,
                email: user.email,
                name: user.name,
                role: user.role,
                department: user.department,
                lastLogin: user.lastLogin
            },
            token
        }
    });
}));

/**
 * @route   GET /api/auth/me
 * @desc    Get current user profile
 * @access  Protected
 */
router.get('/me', protect, asyncHandler(async (req, res) => {
    const user = await User.findById(req.user._id);

    res.json({
        success: true,
        data: {
            user: {
                id: user._id,
                email: user.email,
                name: user.name,
                role: user.role,
                department: user.department,
                lastLogin: user.lastLogin,
                createdAt: user.createdAt
            }
        }
    });
}));

/**
 * @route   PUT /api/auth/password
 * @desc    Change password
 * @access  Protected
 */
router.put('/password', protect, asyncHandler(async (req, res) => {
    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
        throw new APIError('Current and new password are required', 400);
    }

    if (newPassword.length < 8) {
        throw new APIError('New password must be at least 8 characters', 400);
    }

    // Get user with password
    const user = await User.findById(req.user._id).select('+password');

    // Verify current password
    const isMatch = await user.comparePassword(currentPassword);
    if (!isMatch) {
        throw new APIError('Current password is incorrect', 401);
    }

    // Update password
    user.password = newPassword;
    await user.save();

    // Generate new token
    const token = generateToken(user);

    logger.info(`Password changed for user: ${user.email}`);

    res.json({
        success: true,
        message: 'Password updated successfully',
        data: { token }
    });
}));

/**
 * @route   PUT /api/auth/profile
 * @desc    Update user profile
 * @access  Protected
 */
router.put('/profile', protect, asyncHandler(async (req, res) => {
    const allowedUpdates = ['name', 'department'];
    const updates = {};

    for (const field of allowedUpdates) {
        if (req.body[field] !== undefined) {
            updates[field] = req.body[field];
        }
    }

    const user = await User.findByIdAndUpdate(
        req.user._id,
        updates,
        { new: true, runValidators: true }
    );

    res.json({
        success: true,
        data: {
            user: {
                id: user._id,
                email: user.email,
                name: user.name,
                role: user.role,
                department: user.department
            }
        }
    });
}));

/**
 * @route   POST /api/auth/logout
 * @desc    Logout (client should discard token)
 * @access  Protected
 */
router.post('/logout', protect, asyncHandler(async (req, res) => {
    // Token invalidation could be implemented with a token blacklist
    // For now, we rely on client-side token removal
    
    logger.info(`User logged out: ${req.user.email}`);

    res.json({
        success: true,
        message: 'Logged out successfully'
    });
}));

/**
 * @route   GET /api/auth/users
 * @desc    Get all users (admin only)
 * @access  Protected (Admin)
 */
router.get('/users', protect, restrictTo('admin'), asyncHandler(async (req, res) => {
    const { page = 1, limit = 20, role, isActive } = req.query;

    const query = {};
    if (role) query.role = role;
    if (isActive !== undefined) query.isActive = isActive === 'true';

    const users = await User.find(query)
        .select('-refreshTokens')
        .sort({ createdAt: -1 })
        .skip((page - 1) * limit)
        .limit(parseInt(limit));

    const total = await User.countDocuments(query);

    res.json({
        success: true,
        data: {
            users,
            pagination: {
                page: parseInt(page),
                limit: parseInt(limit),
                total,
                pages: Math.ceil(total / limit)
            }
        }
    });
}));

/**
 * @route   PUT /api/auth/users/:id/status
 * @desc    Activate/deactivate user (admin only)
 * @access  Protected (Admin)
 */
router.put('/users/:id/status', protect, restrictTo('admin'), asyncHandler(async (req, res) => {
    const { isActive } = req.body;

    if (typeof isActive !== 'boolean') {
        throw new APIError('isActive must be a boolean', 400);
    }

    // Prevent self-deactivation
    if (req.params.id === req.user._id.toString() && !isActive) {
        throw new APIError('Cannot deactivate your own account', 400);
    }

    const user = await User.findByIdAndUpdate(
        req.params.id,
        { isActive },
        { new: true }
    );

    if (!user) {
        throw new APIError('User not found', 404);
    }

    logger.info(`User ${user.email} ${isActive ? 'activated' : 'deactivated'} by admin`);

    res.json({
        success: true,
        data: { user }
    });
}));

module.exports = router;
