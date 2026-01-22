/**
 * Student Routes (Memory Store Version)
 */

const express = require('express');
const router = express.Router();
const { studentStore, embeddingStore } = require('../store/memoryStore');
const { protect } = require('./auth.memory');
const logger = require('../utils/logger');

const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

/**
 * @route   POST /api/students
 * @desc    Create new student
 */
router.post('/', protect, asyncHandler(async (req, res) => {
  const { studentId, name, email, course, department } = req.body;

  if (!studentId || !name) {
    return res.status(400).json({
      success: false,
      error: 'Student ID and name are required'
    });
  }

  // Check for duplicate
  const existing = await studentStore.findByStudentId(studentId);
  if (existing) {
    return res.status(400).json({
      success: false,
      error: 'Student with this ID already exists'
    });
  }

  const student = await studentStore.create({
    studentId,
    name,
    email,
    course,
    department,
    createdBy: req.user._id
  });

  logger.info(`Student created: ${studentId}`);

  res.status(201).json({
    success: true,
    data: { student }
  });
}));

/**
 * @route   GET /api/students
 * @desc    Get all students
 */
router.get('/', protect, asyncHandler(async (req, res) => {
  const { page = 1, limit = 50, search, enrollmentStatus } = req.query;
  
  const result = await studentStore.findAll({
    search,
    enrollmentStatus,
    skip: (page - 1) * limit,
    limit: parseInt(limit)
  });

  res.json({
    success: true,
    data: {
      students: result.students,
      pagination: {
        total: result.total,
        page: parseInt(page),
        pages: Math.ceil(result.total / limit)
      }
    }
  });
}));

/**
 * @route   GET /api/students/:id
 * @desc    Get student by ID
 */
router.get('/:id', protect, asyncHandler(async (req, res) => {
  const student = await studentStore.findById(req.params.id);

  if (!student) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  res.json({
    success: true,
    data: { student }
  });
}));

/**
 * @route   PUT /api/students/:id
 * @desc    Update student
 */
router.put('/:id', protect, asyncHandler(async (req, res) => {
  const { name, email, course, department } = req.body;

  const student = await studentStore.update(req.params.id, {
    name,
    email,
    course,
    department
  });

  if (!student) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  res.json({
    success: true,
    data: { student }
  });
}));

/**
 * @route   DELETE /api/students/:id
 * @desc    Delete student
 */
router.delete('/:id', protect, asyncHandler(async (req, res) => {
  const deleted = await studentStore.delete(req.params.id);

  if (!deleted) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  logger.info(`Student deleted: ${req.params.id}`);

  res.json({
    success: true,
    message: 'Student deleted successfully'
  });
}));

/**
 * @route   POST /api/students/:id/enrollment/start
 * @desc    Start face enrollment process
 */
router.post('/:id/enrollment/start', protect, asyncHandler(async (req, res) => {
  const { requiredImages = 15 } = req.body;
  
  const student = await studentStore.findById(req.params.id);
  if (!student) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  // Clear any existing temp embeddings
  await embeddingStore.deleteTempByStudent(req.params.id);

  // Update enrollment status
  await studentStore.update(req.params.id, {
    enrollmentStatus: 'in_progress',
    tempEmbeddingsCount: 0,
    requiredImages
  });

  res.json({
    success: true,
    message: 'Enrollment started',
    data: {
      studentId: req.params.id,
      requiredImages,
      capturedCount: 0
    }
  });
}));

/**
 * @route   POST /api/students/:id/enrollment/capture
 * @desc    Capture face image for enrollment
 */
router.post('/:id/enrollment/capture', protect, asyncHandler(async (req, res) => {
  const { imageData } = req.body;

  if (!imageData) {
    return res.status(400).json({
      success: false,
      error: 'Image data is required'
    });
  }

  const student = await studentStore.findById(req.params.id);
  if (!student) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  // Simulate face detection (in real app, this calls AI service)
  // For demo, we'll assume face is always detected
  const faceDetected = true;
  
  if (faceDetected) {
    // Create a dummy embedding (in real app, this comes from InsightFace)
    const dummyEmbedding = Array(512).fill(0).map(() => Math.random() * 2 - 1);
    
    await embeddingStore.create({
      studentId: req.params.id,
      embedding: dummyEmbedding,
      isTemp: true
    });

    const tempEmbeddings = await embeddingStore.findByStudent(req.params.id, true);
    const capturedCount = tempEmbeddings.length;
    const requiredCount = student.requiredImages || 15;

    await studentStore.update(req.params.id, {
      tempEmbeddingsCount: capturedCount
    });

    res.json({
      success: true,
      data: {
        faceDetected: true,
        capturedCount,
        requiredCount,
        complete: capturedCount >= requiredCount
      }
    });
  } else {
    res.json({
      success: true,
      data: {
        faceDetected: false,
        message: 'No face detected in image'
      }
    });
  }
}));

/**
 * @route   POST /api/students/:id/enrollment/complete
 * @desc    Complete enrollment process
 */
router.post('/:id/enrollment/complete', protect, asyncHandler(async (req, res) => {
  const student = await studentStore.findById(req.params.id);
  if (!student) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  const tempEmbeddings = await embeddingStore.findByStudent(req.params.id, true);
  
  if (tempEmbeddings.length < 10) {
    return res.status(400).json({
      success: false,
      error: 'Not enough face captures. Minimum 10 required.'
    });
  }

  // Convert temp to permanent
  await embeddingStore.convertTempToPermanent(req.params.id);

  // Update student status
  await studentStore.update(req.params.id, {
    enrollmentStatus: 'enrolled',
    enrolledAt: new Date(),
    embeddingCount: tempEmbeddings.length
  });

  logger.info(`Student enrolled: ${student.studentId}`);

  res.json({
    success: true,
    message: 'Enrollment completed successfully',
    data: {
      studentId: req.params.id,
      embeddingCount: tempEmbeddings.length
    }
  });
}));

/**
 * @route   POST /api/students/:id/enrollment/reset
 * @desc    Reset enrollment
 */
router.post('/:id/enrollment/reset', protect, asyncHandler(async (req, res) => {
  const student = await studentStore.findById(req.params.id);
  if (!student) {
    return res.status(404).json({
      success: false,
      error: 'Student not found'
    });
  }

  // Delete all embeddings
  await embeddingStore.deleteByStudent(req.params.id);

  // Update status
  await studentStore.update(req.params.id, {
    enrollmentStatus: 'not_enrolled',
    tempEmbeddingsCount: 0,
    embeddingCount: 0
  });

  res.json({
    success: true,
    message: 'Enrollment reset successfully'
  });
}));

module.exports = router;
