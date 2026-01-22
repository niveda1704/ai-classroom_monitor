/**
 * Authentication Routes (Memory Store Version)
 * Handles user registration, login, and token management
 */

const express = require('express');
const router = express.Router();
const jwt = require('jsonwebtoken');
const { userStore } = require('../store/memoryStore');
const config = require('../config');
const logger = require('../utils/logger');

// Helper to generate JWT token
const generateToken = (user) => {
  return jwt.sign(
    { id: user._id, email: user.email, role: user.role },
    config.jwt.secret,
    { expiresIn: config.jwt.expiresIn }
  );
};

// Async handler wrapper
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

// Auth middleware
const protect = async (req, res, next) => {
  try {
    let token;
    
    if (req.headers.authorization?.startsWith('Bearer')) {
      token = req.headers.authorization.split(' ')[1];
    }

    if (!token) {
      return res.status(401).json({ success: false, error: 'Not authorized' });
    }

    const decoded = jwt.verify(token, config.jwt.secret);
    const user = await userStore.findById(decoded.id);

    if (!user) {
      return res.status(401).json({ success: false, error: 'User not found' });
    }

    req.user = user;
    next();
  } catch (error) {
    res.status(401).json({ success: false, error: 'Not authorized' });
  }
};

/**
 * @route   POST /api/auth/register
 * @desc    Register new user
 * @access  Public
 */
router.post('/register', asyncHandler(async (req, res) => {
  const { email, password, name, role, department } = req.body;

  if (!email || !password || !name) {
    return res.status(400).json({
      success: false,
      error: 'Please provide name, email and password'
    });
  }

  // Check if user exists
  const existingUser = await userStore.findByEmail(email);
  if (existingUser) {
    return res.status(400).json({
      success: false,
      error: 'User with this email already exists'
    });
  }

  // Create user
  const user = await userStore.create({
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
        _id: user._id,
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
router.post('/login', asyncHandler(async (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({
      success: false,
      error: 'Please provide email and password'
    });
  }

  // Find user
  const user = await userStore.findByEmail(email);
  if (!user) {
    return res.status(401).json({
      success: false,
      error: 'Invalid credentials'
    });
  }

  // Verify password
  const isMatch = await userStore.comparePassword(user, password);
  if (!isMatch) {
    return res.status(401).json({
      success: false,
      error: 'Invalid credentials'
    });
  }

  // Generate token
  const token = generateToken(user);

  logger.info(`User logged in: ${email}`);

  res.json({
    success: true,
    data: {
      user: {
        _id: user._id,
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
 * @route   GET /api/auth/me
 * @desc    Get current user profile
 * @access  Protected
 */
router.get('/me', protect, asyncHandler(async (req, res) => {
  res.json({
    success: true,
    data: {
      user: {
        _id: req.user._id,
        id: req.user._id,
        email: req.user.email,
        name: req.user.name,
        role: req.user.role,
        department: req.user.department
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
    return res.status(400).json({
      success: false,
      error: 'Current and new password are required'
    });
  }

  // Verify current password
  const isMatch = await userStore.comparePassword(req.user, currentPassword);
  if (!isMatch) {
    return res.status(401).json({
      success: false,
      error: 'Current password is incorrect'
    });
  }

  // Update password
  await userStore.updatePassword(req.user._id, newPassword);

  // Generate new token
  const token = generateToken(req.user);

  logger.info(`Password changed for user: ${req.user.email}`);

  res.json({
    success: true,
    message: 'Password updated successfully',
    data: { token }
  });
}));

module.exports = router;
module.exports.protect = protect;
module.exports.generateToken = generateToken;
