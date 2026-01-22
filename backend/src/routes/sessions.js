/**
 * Session Routes
 * Handles session creation, management, and analytics
 */

const express = require('express');
const router = express.Router();
const axios = require('axios');
const { Session, Event, Snippet, Student } = require('../models');
const { protect, asyncHandler, APIError } = require('../middleware');
const { createSessionValidation, mongoIdParam, paginationValidation } = require('../middleware/validation');
const config = require('../config');
const logger = require('../utils/logger');

/**
 * @route   POST /api/sessions
 * @desc    Create new monitoring session
 * @access  Protected
 */
router.post('/', protect, createSessionValidation, asyncHandler(async (req, res) => {
    const { name, expectedDuration, camera, metadata } = req.body;

    // Check for existing running session
    const runningSession = await Session.findOne({
        faculty: req.user._id,
        status: 'running'
    });

    if (runningSession) {
        throw new APIError('You already have a running session. Please complete it first.', 400);
    }

    const session = await Session.create({
        name,
        faculty: req.user._id,
        expectedDuration,
        camera,
        metadata,
        status: 'created'
    });

    logger.info(`Session created: ${session._id} by ${req.user.email}`);

    res.status(201).json({
        success: true,
        data: { session }
    });
}));

/**
 * @route   GET /api/sessions
 * @desc    Get all sessions for current faculty
 * @access  Protected
 */
router.get('/', protect, paginationValidation, asyncHandler(async (req, res) => {
    const { page = 1, limit = 20, status, startDate, endDate, search } = req.query;

    const query = { faculty: req.user._id };

    if (status) {
        query.status = status;
    }

    if (startDate || endDate) {
        query.createdAt = {};
        if (startDate) query.createdAt.$gte = new Date(startDate);
        if (endDate) query.createdAt.$lte = new Date(endDate);
    }

    if (search) {
        query.$or = [
            { name: { $regex: search, $options: 'i' } },
            { 'metadata.course': { $regex: search, $options: 'i' } },
            { 'metadata.className': { $regex: search, $options: 'i' } }
        ];
    }

    const sessions = await Session.find(query)
        .select('-analytics.studentMetrics -analytics.attention.timeline -analytics.engagement.timeline')
        .sort({ createdAt: -1 })
        .skip((page - 1) * limit)
        .limit(parseInt(limit));

    const total = await Session.countDocuments(query);

    res.json({
        success: true,
        data: {
            sessions,
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
 * @route   GET /api/sessions/:id
 * @desc    Get single session with full details
 * @access  Protected
 */
router.get('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    res.json({
        success: true,
        data: { session }
    });
}));

/**
 * @route   POST /api/sessions/:id/start
 * @desc    Start monitoring session
 * @access  Protected
 */
router.post('/:id/start', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    // Start session
    await session.start();

    // Notify AI service to start monitoring
    try {
        await axios.post(
            `${config.aiService.url}/api/session/start`,
            {
                sessionId: session._id.toString(),
                camera: session.camera,
                expectedDuration: session.expectedDuration
            },
            { timeout: 10000 }
        );
    } catch (error) {
        logger.warn('AI service start notification failed:', error.message);
        // Continue anyway - AI service will be synchronized via WebSocket
    }

    logger.info(`Session started: ${session._id}`);

    res.json({
        success: true,
        data: { 
            session,
            message: 'Session started successfully'
        }
    });
}));

/**
 * @route   POST /api/sessions/:id/pause
 * @desc    Pause monitoring session
 * @access  Protected
 */
router.post('/:id/pause', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    await session.pause();

    // Notify AI service
    try {
        await axios.post(
            `${config.aiService.url}/api/session/pause`,
            { sessionId: session._id.toString() },
            { timeout: 5000 }
        );
    } catch (error) {
        logger.warn('AI service pause notification failed:', error.message);
    }

    res.json({
        success: true,
        data: { session }
    });
}));

/**
 * @route   POST /api/sessions/:id/resume
 * @desc    Resume paused session
 * @access  Protected
 */
router.post('/:id/resume', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    await session.resume();

    // Notify AI service
    try {
        await axios.post(
            `${config.aiService.url}/api/session/resume`,
            { sessionId: session._id.toString() },
            { timeout: 5000 }
        );
    } catch (error) {
        logger.warn('AI service resume notification failed:', error.message);
    }

    res.json({
        success: true,
        data: { session }
    });
}));

/**
 * @route   POST /api/sessions/:id/complete
 * @desc    Complete session and compute final analytics
 * @access  Protected
 */
router.post('/:id/complete', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    // Notify AI service to stop and get final metrics
    let aiAnalytics = null;
    try {
        const aiResponse = await axios.post(
            `${config.aiService.url}/api/session/complete`,
            { sessionId: session._id.toString() },
            { timeout: 30000 }
        );
        aiAnalytics = aiResponse.data.analytics;
    } catch (error) {
        logger.warn('AI service completion failed:', error.message);
    }

    // Compute analytics from events
    const analytics = await computeSessionAnalytics(session._id, aiAnalytics);

    // Complete session with analytics
    await session.complete(analytics);

    // Update event counts
    const eventCounts = await Event.aggregateByType(session._id);
    session.eventCounts = {
        total: eventCounts.reduce((sum, e) => sum + e.count, 0),
        attention: eventCounts.filter(e => e._id.includes('attention')).reduce((sum, e) => sum + e.count, 0),
        distraction: eventCounts.filter(e => e._id === 'distraction').reduce((sum, e) => sum + e.count, 0),
        phoneUsage: eventCounts.filter(e => e._id.includes('phone')).reduce((sum, e) => sum + e.count, 0),
        posture: eventCounts.filter(e => e._id.includes('posture')).reduce((sum, e) => sum + e.count, 0)
    };
    await session.save();

    logger.info(`Session completed: ${session._id}`);

    res.json({
        success: true,
        data: { 
            session,
            summary: {
                duration: session.analytics.totalDuration,
                averageAttention: session.analytics.attention?.average,
                totalEvents: session.eventCounts.total,
                studentsTracked: session.analytics.studentMetrics?.length || 0
            }
        }
    });
}));

/**
 * @route   POST /api/sessions/:id/cancel
 * @desc    Cancel session
 * @access  Protected
 */
router.post('/:id/cancel', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    if (session.status === 'completed') {
        throw new APIError('Cannot cancel completed session', 400);
    }

    session.status = 'cancelled';
    await session.save();

    // Notify AI service
    try {
        await axios.post(
            `${config.aiService.url}/api/session/cancel`,
            { sessionId: session._id.toString() },
            { timeout: 5000 }
        );
    } catch (error) {
        logger.warn('AI service cancel notification failed:', error.message);
    }

    res.json({
        success: true,
        data: { session }
    });
}));

/**
 * @route   DELETE /api/sessions/:id
 * @desc    Delete session and all associated data
 * @access  Protected
 */
router.delete('/:id', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    // Delete associated events
    await Event.deleteMany({ session: session._id });

    // Delete associated snippets (files should be cleaned up separately)
    await Snippet.deleteMany({ session: session._id });

    await session.deleteOne();

    logger.info(`Session deleted: ${req.params.id} by ${req.user.email}`);

    res.json({
        success: true,
        message: 'Session and all associated data deleted'
    });
}));

/**
 * @route   GET /api/sessions/:id/analytics
 * @desc    Get detailed analytics for completed session
 * @access  Protected
 */
router.get('/:id/analytics', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    if (session.status !== 'completed') {
        throw new APIError('Analytics only available for completed sessions', 400);
    }

    // Get event timeline
    const timeline = await Event.getTimeline(session._id, 60000); // 1 minute intervals

    // Get event breakdown
    const eventBreakdown = await Event.aggregateByType(session._id);

    // Get snippet count
    const snippetInfo = await Snippet.getStorageBySession(session._id);

    res.json({
        success: true,
        data: {
            session: {
                id: session._id,
                name: session.name,
                duration: session.analytics.totalDuration,
                startTime: session.actualStartTime,
                endTime: session.actualEndTime
            },
            metrics: session.analytics,
            timeline,
            eventBreakdown,
            snippets: snippetInfo
        }
    });
}));

/**
 * @route   GET /api/sessions/:id/students
 * @desc    Get per-student analytics for session
 * @access  Protected
 */
router.get('/:id/students', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    const studentMetrics = session.analytics?.studentMetrics || [];

    // Enrich with full student data
    const enrichedMetrics = await Promise.all(
        studentMetrics.map(async (metric) => {
            if (metric.studentId) {
                const student = await Student.findById(metric.studentId)
                    .select('studentId name metadata');
                return {
                    ...metric,
                    studentDetails: student
                };
            }
            return metric;
        })
    );

    res.json({
        success: true,
        data: {
            sessionId: session._id,
            studentMetrics: enrichedMetrics
        }
    });
}));

/**
 * @route   GET /api/sessions/:id/events
 * @desc    Get events for a session
 * @access  Protected
 */
router.get('/:id/events', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const { eventTypes, trackId, studentId, limit = 100 } = req.query;

    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    const events = await Event.findBySession(session._id, {
        eventTypes: eventTypes ? eventTypes.split(',') : null,
        trackId: trackId ? parseInt(trackId) : null,
        student: studentId,
        limit: parseInt(limit)
    });

    res.json({
        success: true,
        data: {
            events,
            total: events.length
        }
    });
}));

/**
 * @route   GET /api/sessions/:id/report
 * @desc    Generate downloadable report
 * @access  Protected
 */
router.get('/:id/report', protect, mongoIdParam, asyncHandler(async (req, res) => {
    const { format = 'json' } = req.query;

    const session = await Session.findOne({
        _id: req.params.id,
        faculty: req.user._id
    });

    if (!session) {
        throw new APIError('Session not found', 404);
    }

    if (session.status !== 'completed') {
        throw new APIError('Report only available for completed sessions', 400);
    }

    const timeline = await Event.getTimeline(session._id, 60000);
    const eventBreakdown = await Event.aggregateByType(session._id);

    const report = {
        generatedAt: new Date().toISOString(),
        session: {
            id: session._id,
            name: session.name,
            faculty: req.user.name,
            course: session.metadata?.course,
            className: session.metadata?.className,
            room: session.metadata?.room,
            startTime: session.actualStartTime,
            endTime: session.actualEndTime,
            duration: session.analytics.totalDuration
        },
        summary: {
            averageStudentCount: session.analytics.averageStudentCount,
            peakStudentCount: session.analytics.peakStudentCount,
            averageAttention: session.analytics.attention?.average,
            averageEngagement: session.analytics.engagement?.average,
            totalDistractionTime: session.analytics.distraction?.totalTime,
            phoneUsageEvents: session.analytics.distraction?.phoneUsageEvents
        },
        studentMetrics: session.analytics.studentMetrics,
        eventCounts: session.eventCounts,
        timeline,
        eventBreakdown
    };

    if (format === 'csv') {
        // Generate CSV format
        const csv = generateCSVReport(report);
        res.setHeader('Content-Type', 'text/csv');
        res.setHeader('Content-Disposition', `attachment; filename=session-report-${session._id}.csv`);
        return res.send(csv);
    }

    // Default JSON format
    res.setHeader('Content-Disposition', `attachment; filename=session-report-${session._id}.json`);
    res.json(report);
}));

/**
 * Helper function to compute session analytics
 */
async function computeSessionAnalytics(sessionId, aiAnalytics) {
    const events = await Event.find({ session: sessionId }).lean();
    
    if (events.length === 0) {
        return aiAnalytics || {};
    }

    // Compute attention metrics
    const attentionEvents = events.filter(e => 
        ['attention_high', 'attention_low', 'attention_lost'].includes(e.eventType)
    );

    let attentionAvg = 0;
    if (attentionEvents.length > 0) {
        const highCount = attentionEvents.filter(e => e.eventType === 'attention_high').length;
        attentionAvg = (highCount / attentionEvents.length) * 100;
    }

    // Group events by track ID for per-student metrics
    const trackGroups = {};
    events.forEach(e => {
        if (!trackGroups[e.trackId]) {
            trackGroups[e.trackId] = [];
        }
        trackGroups[e.trackId].push(e);
    });

    const studentMetrics = [];
    for (const [trackId, trackEvents] of Object.entries(trackGroups)) {
        const firstEvent = trackEvents[0];
        const lastEvent = trackEvents[trackEvents.length - 1];
        
        const trackAttention = trackEvents.filter(e => 
            ['attention_high', 'attention_low', 'attention_lost'].includes(e.eventType)
        );
        const highAttention = trackAttention.filter(e => e.eventType === 'attention_high').length;
        
        studentMetrics.push({
            trackId: parseInt(trackId),
            studentId: firstEvent.student,
            name: firstEvent.student ? null : `Track ${trackId}`,
            averageAttention: trackAttention.length > 0 
                ? (highAttention / trackAttention.length) * 100 
                : null,
            distractionCount: trackEvents.filter(e => 
                ['distraction', 'attention_lost'].includes(e.eventType)
            ).length,
            phoneUsageCount: trackEvents.filter(e => 
                e.eventType.includes('phone')
            ).length,
            firstSeen: firstEvent.timestamp,
            lastSeen: lastEvent.timestamp,
            totalTimePresent: Math.floor(
                (new Date(lastEvent.timestamp) - new Date(firstEvent.timestamp)) / 1000
            )
        });
    }

    // Merge with AI analytics if available
    return {
        ...aiAnalytics,
        attention: {
            average: aiAnalytics?.attention?.average || attentionAvg,
            min: aiAnalytics?.attention?.min,
            max: aiAnalytics?.attention?.max
        },
        distraction: {
            phoneUsageEvents: events.filter(e => e.eventType.includes('phone')).length,
            lookingAwayEvents: events.filter(e => 
                ['attention_low', 'attention_lost', 'looking_at_neighbor'].includes(e.eventType)
            ).length
        },
        studentMetrics,
        averageStudentCount: Object.keys(trackGroups).length,
        peakStudentCount: aiAnalytics?.peakStudentCount || Object.keys(trackGroups).length
    };
}

/**
 * Generate CSV report
 */
function generateCSVReport(report) {
    const lines = [];
    
    // Header section
    lines.push('Session Report');
    lines.push(`Generated,${report.generatedAt}`);
    lines.push(`Session Name,${report.session.name}`);
    lines.push(`Faculty,${report.session.faculty}`);
    lines.push(`Course,${report.session.course || 'N/A'}`);
    lines.push(`Duration (seconds),${report.session.duration}`);
    lines.push('');
    
    // Summary section
    lines.push('Summary');
    lines.push(`Average Student Count,${report.summary.averageStudentCount || 'N/A'}`);
    lines.push(`Peak Student Count,${report.summary.peakStudentCount || 'N/A'}`);
    lines.push(`Average Attention (%),${report.summary.averageAttention?.toFixed(1) || 'N/A'}`);
    lines.push(`Phone Usage Events,${report.summary.phoneUsageEvents || 0}`);
    lines.push('');
    
    // Student metrics
    if (report.studentMetrics && report.studentMetrics.length > 0) {
        lines.push('Student Metrics');
        lines.push('Track ID,Name,Avg Attention (%),Distraction Count,Phone Usage,Time Present (s)');
        report.studentMetrics.forEach(s => {
            lines.push([
                s.trackId,
                s.name || 'Unknown',
                s.averageAttention?.toFixed(1) || 'N/A',
                s.distractionCount,
                s.phoneUsageCount,
                s.totalTimePresent
            ].join(','));
        });
    }
    
    return lines.join('\n');
}

module.exports = router;
