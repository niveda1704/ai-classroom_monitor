/**
 * Validation Middleware
 * Request validation using express-validator
 */

const { body, param, query, validationResult } = require('express-validator');

/**
 * Handle validation results
 */
const handleValidation = (req, res, next) => {
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({
            success: false,
            error: 'Validation failed',
            details: errors.array().map(err => ({
                field: err.path,
                message: err.msg
            }))
        });
    }
    next();
};

// ===== Authentication Validators =====

const registerValidation = [
    body('email')
        .isEmail()
        .normalizeEmail()
        .withMessage('Please provide a valid email'),
    body('password')
        .isLength({ min: 8 })
        .withMessage('Password must be at least 8 characters')
        .matches(/^(?=.*\d)(?=.*[a-z])(?=.*[A-Z])/)
        .withMessage('Password must contain uppercase, lowercase, and number'),
    body('name')
        .trim()
        .isLength({ min: 2, max: 100 })
        .withMessage('Name must be between 2 and 100 characters'),
    body('role')
        .optional()
        .isIn(['faculty', 'admin'])
        .withMessage('Invalid role'),
    handleValidation
];

const loginValidation = [
    body('email')
        .isEmail()
        .normalizeEmail()
        .withMessage('Please provide a valid email'),
    body('password')
        .notEmpty()
        .withMessage('Password is required'),
    handleValidation
];

// ===== Student Validators =====

const createStudentValidation = [
    body('studentId')
        .trim()
        .isLength({ min: 1, max: 50 })
        .withMessage('Student ID is required')
        .matches(/^[A-Za-z0-9-_]+$/)
        .withMessage('Student ID can only contain alphanumeric characters, hyphens, and underscores'),
    body('name')
        .trim()
        .isLength({ min: 2, max: 100 })
        .withMessage('Name must be between 2 and 100 characters'),
    body('email')
        .optional()
        .isEmail()
        .normalizeEmail()
        .withMessage('Please provide a valid email'),
    body('metadata.department')
        .optional()
        .trim()
        .isLength({ max: 100 }),
    body('metadata.batch')
        .optional()
        .trim()
        .isLength({ max: 50 }),
    body('metadata.section')
        .optional()
        .trim()
        .isLength({ max: 20 }),
    handleValidation
];

// ===== Session Validators =====

const createSessionValidation = [
    body('name')
        .trim()
        .isLength({ min: 1, max: 200 })
        .withMessage('Session name is required and must be under 200 characters'),
    body('expectedDuration')
        .isInt({ min: 5, max: 480 })
        .withMessage('Duration must be between 5 and 480 minutes'),
    body('camera.deviceId')
        .notEmpty()
        .withMessage('Camera device ID is required'),
    body('camera.label')
        .optional()
        .trim(),
    body('camera.resolution.width')
        .optional()
        .isInt({ min: 320, max: 3840 }),
    body('camera.resolution.height')
        .optional()
        .isInt({ min: 240, max: 2160 }),
    body('metadata.course')
        .optional()
        .trim()
        .isLength({ max: 100 }),
    body('metadata.className')
        .optional()
        .trim()
        .isLength({ max: 100 }),
    body('metadata.room')
        .optional()
        .trim()
        .isLength({ max: 50 }),
    body('metadata.notes')
        .optional()
        .trim()
        .isLength({ max: 500 }),
    handleValidation
];

// ===== Event Validators =====

const createEventValidation = [
    body('sessionId')
        .isMongoId()
        .withMessage('Valid session ID is required'),
    body('trackId')
        .isInt({ min: 0 })
        .withMessage('Track ID must be a non-negative integer'),
    body('eventType')
        .isIn([
            'attention_high', 'attention_low', 'attention_lost',
            'phone_detected', 'phone_usage_start', 'phone_usage_end',
            'posture_good', 'posture_poor', 'drowsiness_detected',
            'hand_raised', 'student_entered', 'student_left',
            'engagement_high', 'engagement_low', 'distraction',
            'talking', 'looking_at_neighbor'
        ])
        .withMessage('Invalid event type'),
    body('confidence')
        .isFloat({ min: 0, max: 1 })
        .withMessage('Confidence must be between 0 and 1'),
    body('timestamp')
        .isISO8601()
        .withMessage('Valid timestamp is required'),
    handleValidation
];

// ===== Query Validators =====

const paginationValidation = [
    query('page')
        .optional()
        .isInt({ min: 1 })
        .withMessage('Page must be a positive integer'),
    query('limit')
        .optional()
        .isInt({ min: 1, max: 100 })
        .withMessage('Limit must be between 1 and 100'),
    handleValidation
];

const mongoIdParam = [
    param('id')
        .isMongoId()
        .withMessage('Invalid ID format'),
    handleValidation
];

module.exports = {
    handleValidation,
    registerValidation,
    loginValidation,
    createStudentValidation,
    createSessionValidation,
    createEventValidation,
    paginationValidation,
    mongoIdParam
};
