/**
 * Event Routes
 * Handles event creation and querying
 */

const express = require('express');
const router = express.Router();
const { Event, Session, Snippet } = require('../models');
const { protect, asyncHandler, APIError } = require('../middleware');
const { createEventValidation, mongoIdParam } = require('../middleware/validation');
const logger = require('../utils/logger');

/**
 * @route   POST /api/events
 * @desc    Create new event (called by AI service)
 * @access  Protected
 */
router.post('/', protect, createEventValidation, asyncHandler(async (req, res) => {
    const {
        sessionId,
        trackId,
        studentId,
        eventType,
        confidence,
        timestamp,
        boundingBox,
        data,
        snippetId
    } = req.body;

    // Verify session belongs to user and is running
    const session = await Session.findOne({
        _id: sessionId,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    if (session.status !== 'running') {
        throw new APIError('Session is not running', 400);
    }

    // Calculate session offset
    const sessionOffset = new Date(timestamp) - session.actualStartTime;

    const event = await Event.create({
        session: sessionId,
        trackId,
        student: studentId || null,
        eventType,
        confidence,
        timestamp: new Date(timestamp),
        sessionOffset,
        boundingBox,
        data,
        snippet: snippetId || null
    });

    // Update session event counts
    session.eventCounts.total += 1;
    if (eventType.includes('attention')) session.eventCounts.attention += 1;
    if (eventType === 'distraction') session.eventCounts.distraction += 1;
    if (eventType.includes('phone')) session.eventCounts.phoneUsage += 1;
    if (eventType.includes('posture')) session.eventCounts.posture += 1;
    await session.save();

    res.status(201).json({
        success: true,
        data: { event }
    });
}));

/**
 * @route   POST /api/events/batch
 * @desc    Create multiple events at once (for efficiency)
 * @access  Protected
 */
router.post('/batch', protect, asyncHandler(async (req, res) => {
    const { sessionId, events } = req.body;

    if (!sessionId || !events || !Array.isArray(events)) {
        throw new APIError('Session ID and events array required', 400);
    }

    // Verify session
    const session = await Session.findOne({
        _id: sessionId,
        faculty: req.user._id,
        status: 'running'
    });

    if (!session) {
        throw new APIError('Running session not found', 404);
    }

    // Process events
    const eventDocs = events.map(e => ({
        session: sessionId,
        trackId: e.trackId,
        student: e.studentId || null,
        eventType: e.eventType,
        confidence: e.confidence,
        timestamp: new Date(e.timestamp),
        sessionOffset: new Date(e.timestamp) - session.actualStartTime,
        boundingBox: e.boundingBox,
        data: e.data
    }));

    const createdEvents = await Event.insertMany(eventDocs);

    // Update session event counts
    const counts = {
        total: events.length,
        attention: events.filter(e => e.eventType.includes('attention')).length,
        distraction: events.filter(e => e.eventType === 'distraction').length,
        phoneUsage: events.filter(e => e.eventType.includes('phone')).length,
        posture: events.filter(e => e.eventType.includes('posture')).length
    };

    session.eventCounts.total += counts.total;
    session.eventCounts.attention += counts.attention;
    session.eventCounts.distraction += counts.distraction;
    session.eventCounts.phoneUsage += counts.phoneUsage;
    session.eventCounts.posture += counts.posture;
    await session.save();

    res.status(201).json({
        success: true,
        data: {
            created: createdEvents.length,
            counts
        }
    });
}));

/**
 * @route   GET /api/events/:id
 * @desc    Get single event
 * @access  Protected
 */
router.get('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const event = await Event.findById(req.params.id)
        .populate('student', 'studentId name')
        .populate('snippet', 'filename duration');

    if (!event) {
        throw new APIError('Event not found', 404);
    }

    // Verify access
    const session = await Session.findOne({
        _id: event.session,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Access denied', 403);
    }

    res.json({
        success: true,
        data: { event }
    });
}));

/**
 * @route   GET /api/events/session/:sessionId/summary
 * @desc    Get event summary for a session
 * @access  Protected
 */
router.get('/session/:sessionId/summary', protect, asyncHandler(async (req, res) => {
    const { sessionId } = req.params;

    // Verify session access
    const session = await Session.findOne({
        _id: sessionId,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    const summary = await Event.aggregateByType(sessionId);

    // Get timeline data
    const timeline = await Event.getTimeline(sessionId, 60000);

    // Get unique track IDs
    const uniqueTracks = await Event.distinct('trackId', { session: sessionId });

    // Get identified students
    const identifiedStudents = await Event.distinct('student', { 
        session: sessionId,
        student: { $ne: null }
    });

    res.json({
        success: true,
        data: {
            eventSummary: summary,
            timeline,
            stats: {
                totalEvents: summary.reduce((sum, e) => sum + e.count, 0),
                uniqueTracks: uniqueTracks.length,
                identifiedStudents: identifiedStudents.length,
                timespan: timeline.length > 0 ? {
                    start: timeline[0].time,
                    end: timeline[timeline.length - 1].time
                } : null
            }
        }
    });
}));

/**
 * @route   GET /api/events/session/:sessionId/timeline
 * @desc    Get event timeline for visualization
 * @access  Protected
 */
router.get('/session/:sessionId/timeline', protect, asyncHandler(async (req, res) => {
    const { sessionId } = req.params;
    const { interval = 60000 } = req.query; // Default 1 minute intervals

    // Verify session access
    const session = await Session.findOne({
        _id: sessionId,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    const timeline = await Event.getTimeline(sessionId, parseInt(interval));

    res.json({
        success: true,
        data: { timeline }
    });
}));

/**
 * @route   GET /api/events/session/:sessionId/track/:trackId
 * @desc    Get all events for a specific track
 * @access  Protected
 */
router.get('/session/:sessionId/track/:trackId', protect, asyncHandler(async (req, res) => {
    const { sessionId, trackId } = req.params;

    // Verify session access
    const session = await Session.findOne({
        _id: sessionId,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    const events = await Event.find({
        session: sessionId,
        trackId: parseInt(trackId)
    })
        .sort({ timestamp: 1 })
        .populate('student', 'studentId name')
        .populate('snippet', 'filename duration');

    res.json({
        success: true,
        data: {
            trackId: parseInt(trackId),
            events,
            total: events.length
        }
    });
}));

/**
 * @route   DELETE /api/events/:id
 * @desc    Delete an event
 * @access  Protected
 */
router.delete('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const event = await Event.findById(req.params.id);

    if (!event) {
        throw new APIError('Event not found', 404);
    }

    // Verify access
    const session = await Session.findOne({
        _id: event.session,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Access denied', 403);
    }

    await event.deleteOne();

    res.json({
        success: true,
        message: 'Event deleted'
    });
}));

module.exports = router;
