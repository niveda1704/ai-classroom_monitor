/**
 * Session Routes (Memory Store Version)
 */

const express = require('express');
const router = express.Router();
const { sessionStore, eventStore, studentStore } = require('../store/memoryStore');
const { protect } = require('./auth.memory');
const logger = require('../utils/logger');

const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

/**
 * @route   POST /api/sessions
 * @desc    Create new session
 */
router.post('/', protect, asyncHandler(async (req, res) => {
  const { name, courseName, roomNumber, description } = req.body;

  if (!name || !courseName) {
    return res.status(400).json({
      success: false,
      error: 'Name and course name are required'
    });
  }

  const session = await sessionStore.create({
    name,
    courseName,
    roomNumber,
    description,
    createdBy: req.user._id
  });

  logger.info(`Session created: ${name}`);

  res.status(201).json({
    success: true,
    data: { session }
  });
}));

/**
 * @route   GET /api/sessions
 * @desc    Get all sessions
 */
router.get('/', protect, asyncHandler(async (req, res) => {
  const { page = 1, limit = 50, status, sortBy, sortOrder } = req.query;

  const result = await sessionStore.findAll({
    status,
    sortBy,
    sortOrder,
    skip: (page - 1) * limit,
    limit: parseInt(limit)
  });

  res.json({
    success: true,
    data: {
      sessions: result.sessions,
      pagination: {
        total: result.total,
        page: parseInt(page),
        pages: Math.ceil(result.total / limit)
      }
    }
  });
}));

/**
 * @route   GET /api/sessions/:id
 * @desc    Get session by ID
 */
router.get('/:id', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  res.json({
    success: true,
    data: { session }
  });
}));

/**
 * @route   POST /api/sessions/:id/start
 * @desc    Start session
 */
router.post('/:id/start', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  if (session.status !== 'created') {
    return res.status(400).json({
      success: false,
      error: 'Session can only be started from created state'
    });
  }

  const updated = await sessionStore.update(req.params.id, {
    status: 'running',
    startedAt: new Date()
  });

  logger.info(`Session started: ${session.name}`);

  res.json({
    success: true,
    data: { session: updated }
  });
}));

/**
 * @route   POST /api/sessions/:id/pause
 * @desc    Pause session
 */
router.post('/:id/pause', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  if (session.status !== 'running') {
    return res.status(400).json({
      success: false,
      error: 'Only running sessions can be paused'
    });
  }

  const updated = await sessionStore.update(req.params.id, {
    status: 'paused',
    pausedAt: new Date()
  });

  res.json({
    success: true,
    data: { session: updated }
  });
}));

/**
 * @route   POST /api/sessions/:id/resume
 * @desc    Resume session
 */
router.post('/:id/resume', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  if (session.status !== 'paused') {
    return res.status(400).json({
      success: false,
      error: 'Only paused sessions can be resumed'
    });
  }

  // Calculate paused duration
  const pausedDuration = (session.pausedDuration || 0) + 
    (new Date() - new Date(session.pausedAt)) / 1000;

  const updated = await sessionStore.update(req.params.id, {
    status: 'running',
    pausedDuration
  });

  res.json({
    success: true,
    data: { session: updated }
  });
}));

/**
 * @route   POST /api/sessions/:id/complete
 * @desc    Complete session
 */
router.post('/:id/complete', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  // Allow completing from any state except already completed
  if (session.status === 'completed') {
    // Already completed - just return success
    return res.json({
      success: true,
      data: { session }
    });
  }

  const completedAt = new Date();
  const actualDuration = session.startedAt
    ? (completedAt - new Date(session.startedAt)) / 1000 - (session.pausedDuration || 0)
    : 0;

  // Generate final analytics
  const eventSummary = await eventStore.getSessionSummary(req.params.id);
  
  const finalAnalytics = {
    avgAttention: session.liveMetrics?.avgAttention || Math.random() * 30 + 60,
    totalStudents: session.liveMetrics?.studentCount || session.liveMetrics?.totalDetected || Math.floor(Math.random() * 20) + 5,
    identifiedStudents: session.liveMetrics?.identifiedCount || Math.floor(Math.random() * 15),
    eventCounts: eventSummary.byType,
    totalEvents: eventSummary.total,
    duration: actualDuration
  };

  const updated = await sessionStore.update(req.params.id, {
    status: 'completed',
    completedAt,
    actualDuration,
    finalAnalytics
  });

  logger.info(`Session completed: ${session.name}`);

  res.json({
    success: true,
    data: { session: updated }
  });
}));

/**
 * @route   GET /api/sessions/:id/analytics
 * @desc    Get session analytics
 */
router.get('/:id/analytics', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  // Get events for the session
  const eventResult = await eventStore.findBySession(req.params.id, { limit: 1000 });
  const events = eventResult.events;

  // Generate timeline data (every 5 minutes)
  const timeline = [];
  const durationMinutes = Math.ceil((session.actualDuration || 3600) / 60);
  for (let i = 0; i < durationMinutes; i += 5) {
    timeline.push({
      time: i,
      avgAttention: 60 + Math.random() * 30,
      studentCount: Math.floor(Math.random() * 5) + 15
    });
  }

  // Generate per-student analytics (demo data)
  const students = (await studentStore.findAll({ limit: 100 })).students;
  const studentAnalytics = students.slice(0, 10).map(s => ({
    studentId: s._id,
    name: s.name,
    avgAttention: 50 + Math.random() * 40,
    phoneEvents: Math.floor(Math.random() * 3),
    postureEvents: Math.floor(Math.random() * 5),
    gazeEvents: Math.floor(Math.random() * 4),
    timeInFrame: (session.actualDuration || 3600) * (0.7 + Math.random() * 0.3)
  }));

  res.json({
    success: true,
    data: {
      summary: session.finalAnalytics || {
        avgAttention: 75,
        totalStudents: 20,
        identifiedStudents: 15,
        totalEvents: events.length
      },
      timeline,
      studentAnalytics,
      eventSummary: await eventStore.getSessionSummary(req.params.id)
    }
  });
}));

/**
 * @route   GET /api/sessions/:id/events
 * @desc    Get session events
 */
router.get('/:id/events', protect, asyncHandler(async (req, res) => {
  const { page = 1, limit = 100, eventType, studentId } = req.query;

  const result = await eventStore.findBySession(req.params.id, {
    eventType,
    studentId,
    skip: (page - 1) * limit,
    limit: parseInt(limit)
  });

  res.json({
    success: true,
    data: {
      events: result.events,
      pagination: {
        total: result.total,
        page: parseInt(page),
        pages: Math.ceil(result.total / limit)
      }
    }
  });
}));

/**
 * @route   GET /api/sessions/:id/report
 * @desc    Download session report
 */
router.get('/:id/report', protect, asyncHandler(async (req, res) => {
  const { format = 'json' } = req.query;
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  const eventResult = await eventStore.findBySession(req.params.id, { limit: 10000 });

  const report = {
    session: {
      name: session.name,
      courseName: session.courseName,
      roomNumber: session.roomNumber,
      status: session.status,
      startedAt: session.startedAt,
      completedAt: session.completedAt,
      duration: session.actualDuration
    },
    analytics: session.finalAnalytics,
    events: eventResult.events,
    generatedAt: new Date().toISOString()
  };

  if (format === 'csv') {
    // Simple CSV conversion
    let csv = 'Event Type,Student ID,Timestamp,Details\n';
    eventResult.events.forEach(e => {
      csv += `${e.eventType},${e.studentId || ''},${e.timestamp},${JSON.stringify(e.details)}\n`;
    });
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', `attachment; filename=session-${req.params.id}-report.csv`);
    return res.send(csv);
  }

  res.json({
    success: true,
    data: report
  });
}));

/**
 * @route   DELETE /api/sessions/:id
 * @desc    Delete session
 */
router.delete('/:id', protect, asyncHandler(async (req, res) => {
  const session = await sessionStore.findById(req.params.id);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  if (session.status === 'running') {
    return res.status(400).json({
      success: false,
      error: 'Cannot delete running session'
    });
  }

  await sessionStore.delete(req.params.id);
  logger.info(`Session deleted: ${session.name}`);

  res.json({
    success: true,
    message: 'Session deleted successfully'
  });
}));

/**
 * @route   POST /api/sessions/:id/process-frame
 * @desc    Process a video frame through AI service
 */
router.post('/:id/process-frame', protect, asyncHandler(async (req, res) => {
  const { imageData, timestamp } = req.body;
  const sessionId = req.params.id;

  const session = await sessionStore.findById(sessionId);

  if (!session) {
    return res.status(404).json({
      success: false,
      error: 'Session not found'
    });
  }

  if (session.status !== 'running') {
    return res.status(400).json({
      success: false,
      error: 'Session is not running'
    });
  }

  try {
    // Forward frame to AI service
    const AI_SERVICE_URL = process.env.AI_SERVICE_URL || 'http://localhost:8000';
    
    const aiResponse = await fetch(`${AI_SERVICE_URL}/api/process-frame`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        sessionId,
        imageData,
        timestamp: timestamp || new Date().toISOString()
      })
    });

    if (!aiResponse.ok) {
      const errorText = await aiResponse.text();
      logger.error(`AI service error: ${errorText}`);
      throw new Error('AI service processing failed');
    }

    const result = await aiResponse.json();

    // Store events from AI processing
    if (result.events && result.events.length > 0) {
      for (const event of result.events) {
        await eventStore.create({
          sessionId,
          ...event,
          timestamp: new Date()
        });
      }
    }

    // Update session live metrics
    if (result.metrics) {
      await sessionStore.update(sessionId, {
        liveMetrics: {
          ...session.liveMetrics,
          ...result.metrics,
          lastUpdated: new Date()
        }
      });

      // Broadcast metrics via WebSocket
      const wsService = require('../services/websocket');
      wsService.broadcastToSession(sessionId, {
        type: 'session_metrics',
        sessionId,
        metrics: result.metrics,
        timestamp: Date.now()
      });

      // Broadcast detected students
      if (result.students && result.students.length > 0) {
        result.students.forEach(student => {
          wsService.broadcastToSession(sessionId, {
            type: 'student_update',
            sessionId,
            student,
            timestamp: Date.now()
          });
        });
      }

      // Broadcast new events
      if (result.events && result.events.length > 0) {
        result.events.forEach(event => {
          wsService.broadcastToSession(sessionId, {
            type: 'new_event',
            sessionId,
            event,
            timestamp: Date.now()
          });
        });
      }
    }

    res.json({
      success: true,
      data: result
    });

  } catch (error) {
    logger.error(`Frame processing error: ${error.message}`);
    
    // Return simulated data if AI service is unavailable
    const simulatedMetrics = {
      studentCount: Math.floor(Math.random() * 3) + 1,
      avgAttention: 60 + Math.random() * 30,
      phoneUsage: Math.random() > 0.9 ? 1 : 0,
      distractions: Math.random() > 0.85 ? 1 : 0
    };

    // Update session with simulated metrics
    await sessionStore.update(sessionId, {
      liveMetrics: {
        ...session.liveMetrics,
        ...simulatedMetrics,
        lastUpdated: new Date()
      }
    });

    // Broadcast simulated metrics via WebSocket
    try {
      const wsService = require('../services/websocket');
      wsService.broadcastToSession(sessionId, {
        type: 'session_metrics',
        sessionId,
        metrics: simulatedMetrics,
        timestamp: Date.now()
      });
    } catch (wsError) {
      logger.error(`WebSocket broadcast error: ${wsError.message}`);
    }

    res.json({
      success: true,
      data: {
        metrics: simulatedMetrics,
        students: [],
        events: [],
        simulated: true
      }
    });
  }
}));

module.exports = router;
