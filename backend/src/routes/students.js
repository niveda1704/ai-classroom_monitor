/**
 * Student Routes
 * Handles student management and enrollment
 */

const express = require('express');
const router = express.Router();
const axios = require('axios');
const { Student, Embedding } = require('../models');
const { protect, asyncHandler, APIError } = require('../middleware');
const { createStudentValidation, mongoIdParam, paginationValidation } = require('../middleware/validation');
const config = require('../config');
const logger = require('../utils/logger');

/**
 * @route   POST /api/students
 * @desc    Create new student (starts enrollment process)
 * @access  Protected
 */
router.post('/', protect, createStudentValidation, asyncHandler(async (req, res) => {
    const { studentId, name, email, metadata } = req.body;

    // Check if student ID exists
    const existingStudent = await Student.findOne({ studentId: studentId.toUpperCase() });
    if (existingStudent) {
        throw new APIError('Student with this ID already exists', 400, 'STUDENT_EXISTS');
    }

    // Create student
    const student = await Student.create({
        studentId: studentId.toUpperCase(),
        name,
        email,
        metadata,
        enrolledBy: req.user._id,
        enrollmentStatus: 'pending'
    });

    logger.info(`Student created: ${studentId} by ${req.user.email}`);

    res.status(201).json({
        success: true,
        data: { student }
    });
}));

/**
 * @route   GET /api/students
 * @desc    Get all students (for current faculty)
 * @access  Protected
 */
router.get('/', protect, paginationValidation, asyncHandler(async (req, res) => {
    const { page = 1, limit = 20, search, status, department } = req.query;

    const query = { enrolledBy: req.user._id };

    // Search by name or student ID
    if (search) {
        query.$or = [
            { name: { $regex: search, $options: 'i' } },
            { studentId: { $regex: search, $options: 'i' } }
        ];
    }

    if (status) {
        query.enrollmentStatus = status;
    }

    if (department) {
        query['metadata.department'] = department;
    }

    const students = await Student.find(query)
        .populate('embeddingId', 'quality createdAt')
        .sort({ name: 1 })
        .skip((page - 1) * limit)
        .limit(parseInt(limit));

    const total = await Student.countDocuments(query);

    res.json({
        success: true,
        data: {
            students,
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
 * @route   GET /api/students/:id
 * @desc    Get single student
 * @access  Protected
 */
router.get('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const student = await Student.findOne({
        _id: req.params.id,
        enrolledBy: req.user._id
    }).populate('embeddingId');

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    res.json({
        success: true,
        data: { student }
    });
}));

/**
 * @route   PUT /api/students/:id
 * @desc    Update student
 * @access  Protected
 */
router.put('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const allowedUpdates = ['name', 'email', 'metadata', 'isActive'];
    const updates = {};

    for (const field of allowedUpdates) {
        if (req.body[field] !== undefined) {
            updates[field] = req.body[field];
        }
    }

    const student = await Student.findOneAndUpdate(
        { _id: req.params.id, enrolledBy: req.user._id },
        updates,
        { new: true, runValidators: true }
    );

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    res.json({
        success: true,
        data: { student }
    });
}));

/**
 * @route   DELETE /api/students/:id
 * @desc    Delete student and their embedding
 * @access  Protected
 */
router.delete('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const student = await Student.findOne({
        _id: req.params.id,
        enrolledBy: req.user._id
    });

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    // Delete associated embedding
    if (student.embeddingId) {
        await Embedding.findByIdAndDelete(student.embeddingId);
    }

    await student.deleteOne();

    logger.info(`Student deleted: ${student.studentId} by ${req.user.email}`);

    res.json({
        success: true,
        message: 'Student deleted successfully'
    });
}));

/**
 * @route   POST /api/students/:id/enrollment/start
 * @desc    Start face enrollment capture process
 * @access  Protected
 */
router.post('/:id/enrollment/start', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const student = await Student.findOne({
        _id: req.params.id,
        enrolledBy: req.user._id
    });

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    if (student.enrollmentStatus === 'completed') {
        throw new APIError('Student is already enrolled', 400);
    }

    // Reset enrollment progress
    student.enrollmentStatus = 'capturing';
    student.enrollmentProgress = {
        capturedImages: 0,
        requiredImages: req.body.requiredImages || 15
    };
    await student.save();

    res.json({
        success: true,
        data: {
            studentId: student._id,
            requiredImages: student.enrollmentProgress.requiredImages,
            message: 'Enrollment capture started. Send face images to /api/students/:id/enrollment/capture'
        }
    });
}));

/**
 * @route   POST /api/students/:id/enrollment/capture
 * @desc    Capture face image for enrollment (sends to AI service)
 * @access  Protected
 */
router.post('/:id/enrollment/capture', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const { imageData } = req.body; // Base64 encoded image

    if (!imageData) {
        throw new APIError('Image data is required', 400);
    }

    const student = await Student.findOne({
        _id: req.params.id,
        enrolledBy: req.user._id
    });

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    if (student.enrollmentStatus !== 'capturing') {
        throw new APIError('Enrollment not in capture mode. Start enrollment first.', 400);
    }

    try {
        // Send image to AI service for face detection and quality check
        const aiResponse = await axios.post(
            `${config.aiService.url}/api/enrollment/capture`,
            {
                studentId: student._id.toString(),
                imageData,
                captureIndex: student.enrollmentProgress.capturedImages
            },
            { timeout: config.aiService.timeout }
        );

        if (aiResponse.data.success && aiResponse.data.faceDetected) {
            // Update capture count
            student.enrollmentProgress.capturedImages += 1;
            await student.save();

            // Check if we have enough images
            const isComplete = student.enrollmentProgress.capturedImages >= 
                               student.enrollmentProgress.requiredImages;

            res.json({
                success: true,
                data: {
                    captured: student.enrollmentProgress.capturedImages,
                    required: student.enrollmentProgress.requiredImages,
                    faceQuality: aiResponse.data.faceQuality,
                    isComplete,
                    message: isComplete 
                        ? 'All images captured. Call /api/students/:id/enrollment/complete to finalize.'
                        : `Image ${student.enrollmentProgress.capturedImages} captured successfully`
                }
            });
        } else {
            res.json({
                success: false,
                error: aiResponse.data.error || 'No face detected in image',
                data: {
                    captured: student.enrollmentProgress.capturedImages,
                    required: student.enrollmentProgress.requiredImages
                }
            });
        }
    } catch (error) {
        logger.error('AI service enrollment error:', error.message);
        throw new APIError('Failed to process image. AI service unavailable.', 503);
    }
}));

/**
 * @route   POST /api/students/:id/enrollment/complete
 * @desc    Complete enrollment - compute averaged embedding
 * @access  Protected
 */
router.post('/:id/enrollment/complete', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const student = await Student.findOne({
        _id: req.params.id,
        enrolledBy: req.user._id
    });

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    if (student.enrollmentProgress.capturedImages < 10) {
        throw new APIError('Minimum 10 face captures required', 400);
    }

    student.enrollmentStatus = 'processing';
    await student.save();

    try {
        // Request AI service to compute averaged embedding
        const aiResponse = await axios.post(
            `${config.aiService.url}/api/enrollment/complete`,
            { studentId: student._id.toString() },
            { timeout: 60000 } // Longer timeout for embedding computation
        );

        if (aiResponse.data.success) {
            // Create embedding document
            const embedding = await Embedding.create({
                studentId: student._id,
                embedding: aiResponse.data.embedding,
                quality: {
                    averageConfidence: aiResponse.data.quality.averageConfidence,
                    imagesUsed: aiResponse.data.quality.imagesUsed,
                    consistency: aiResponse.data.quality.consistency
                },
                modelInfo: {
                    name: aiResponse.data.modelInfo?.name || 'buffalo_l',
                    version: aiResponse.data.modelInfo?.version
                },
                isNormalized: true
            });

            // Update student
            student.embeddingId = embedding._id;
            student.enrollmentStatus = 'completed';
            await student.save();

            logger.info(`Enrollment completed for student: ${student.studentId}`);

            res.json({
                success: true,
                data: {
                    student: {
                        id: student._id,
                        studentId: student.studentId,
                        name: student.name,
                        enrollmentStatus: 'completed'
                    },
                    embeddingQuality: embedding.quality
                }
            });
        } else {
            student.enrollmentStatus = 'failed';
            await student.save();
            throw new APIError(aiResponse.data.error || 'Embedding computation failed', 500);
        }
    } catch (error) {
        if (error instanceof APIError) throw error;
        
        student.enrollmentStatus = 'failed';
        await student.save();
        
        logger.error('Enrollment completion error:', error.message);
        throw new APIError('Failed to complete enrollment. Please try again.', 503);
    }
}));

/**
 * @route   POST /api/students/:id/enrollment/reset
 * @desc    Reset enrollment for re-capture
 * @access  Protected
 */
router.post('/:id/enrollment/reset', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const student = await Student.findOne({
        _id: req.params.id,
        enrolledBy: req.user._id
    });

    if (!student) {
        throw new APIError('Student not found', 404);
    }

    // Delete existing embedding
    if (student.embeddingId) {
        await Embedding.findByIdAndDelete(student.embeddingId);
    }

    // Notify AI service to clear temporary captures
    try {
        await axios.post(
            `${config.aiService.url}/api/enrollment/reset`,
            { studentId: student._id.toString() },
            { timeout: 5000 }
        );
    } catch (error) {
        logger.warn('AI service reset notification failed:', error.message);
    }

    // Reset student enrollment
    student.embeddingId = null;
    student.enrollmentStatus = 'pending';
    student.enrollmentProgress = {
        capturedImages: 0,
        requiredImages: 15
    };
    await student.save();

    logger.info(`Enrollment reset for student: ${student.studentId}`);

    res.json({
        success: true,
        message: 'Enrollment reset successfully'
    });
}));

/**
 * @route   GET /api/students/enrolled/count
 * @desc    Get count of enrolled students
 * @access  Protected
 */
router.get('/enrolled/count', protect, asyncHandler(async (req, res) => {
    const total = await Student.countDocuments({ enrolledBy: req.user._id });
    const enrolled = await Student.countDocuments({ 
        enrolledBy: req.user._id,
        enrollmentStatus: 'completed'
    });
    const pending = await Student.countDocuments({
        enrolledBy: req.user._id,
        enrollmentStatus: { $in: ['pending', 'capturing', 'processing'] }
    });

    res.json({
        success: true,
        data: {
            total,
            enrolled,
            pending,
            failed: total - enrolled - pending
        }
    });
}));

module.exports = router;
