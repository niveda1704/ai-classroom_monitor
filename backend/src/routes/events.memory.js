/**
 * Event Routes (Memory Store Version)
 */

const express = require('express');
const router = express.Router();
const { eventStore } = require('../store/memoryStore');
const { protect } = require('./auth.memory');

const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

/**
 * @route   POST /api/events
 * @desc    Create single event
 */
router.post('/', protect, asyncHandler(async (req, res) => {
  const { sessionId, studentId, trackId, eventType, details, confidence, timestamp, frameNumber } = req.body;

  if (!sessionId || !eventType) {
    return res.status(400).json({
      success: false,
      error: 'Session ID and event type are required'
    });
  }

  const event = await eventStore.create({
    sessionId,
    studentId,
    trackId,
    eventType,
    details,
    confidence,
    timestamp,
    frameNumber
  });

  res.status(201).json({
    success: true,
    data: { event }
  });
}));

/**
 * @route   POST /api/events/batch
 * @desc    Create batch events
 */
router.post('/batch', protect, asyncHandler(async (req, res) => {
  const { events } = req.body;

  if (!events || !Array.isArray(events) || events.length === 0) {
    return res.status(400).json({
      success: false,
      error: 'Events array is required'
    });
  }

  const created = await eventStore.createBatch(events);

  res.status(201).json({
    success: true,
    data: {
      count: created.length,
      events: created
    }
  });
}));

/**
 * @route   GET /api/events/session/:sessionId/summary
 * @desc    Get event summary for session
 */
router.get('/session/:sessionId/summary', protect, asyncHandler(async (req, res) => {
  const summary = await eventStore.getSessionSummary(req.params.sessionId);

  res.json({
    success: true,
    data: { summary }
  });
}));

/**
 * @route   GET /api/events/session/:sessionId/timeline
 * @desc    Get event timeline for session
 */
router.get('/session/:sessionId/timeline', protect, asyncHandler(async (req, res) => {
  const result = await eventStore.findBySession(req.params.sessionId, { limit: 1000 });

  // Group events by time buckets (5 minute intervals)
  const timeline = {};
  result.events.forEach(event => {
    const timestamp = new Date(event.timestamp);
    const bucket = Math.floor(timestamp.getMinutes() / 5) * 5;
    const key = `${timestamp.getHours()}:${bucket.toString().padStart(2, '0')}`;
    
    if (!timeline[key]) {
      timeline[key] = { time: key, events: [] };
    }
    timeline[key].events.push(event);
  });

  res.json({
    success: true,
    data: {
      timeline: Object.values(timeline),
      totalEvents: result.total
    }
  });
}));

module.exports = router;
