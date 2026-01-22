/**
 * Event Model
 * Stores timestamped events during monitoring sessions
 */

const mongoose = require('mongoose');

const eventSchema = new mongoose.Schema({
    session: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Session',
        required: true,
        index: true
    },
    // ByteTrack track ID for the detected person
    trackId: {
        type: Number,
        required: true
    },
    // Matched student (if identified via embedding)
    student: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Student',
        sparse: true
    },
    // Event classification
    eventType: {
        type: String,
        enum: [
            'attention_high',      // Looking at instructor/board
            'attention_low',       // Looking away
            'attention_lost',      // Completely disengaged
            'phone_detected',      // Phone usage detected
            'phone_usage_start',   // Started using phone
            'phone_usage_end',     // Stopped using phone
            'posture_good',        // Good sitting posture
            'posture_poor',        // Slouching or poor posture
            'drowsiness_detected', // Signs of drowsiness
            'hand_raised',         // Student raised hand
            'student_entered',     // New student detected
            'student_left',        // Student left frame
            'engagement_high',     // Highly engaged
            'engagement_low',      // Low engagement
            'distraction',         // General distraction
            'talking',             // Student talking
            'looking_at_neighbor'  // Looking at another student
        ],
        required: true
    },
    // Detection confidence (0-1)
    confidence: {
        type: Number,
        required: true,
        min: 0,
        max: 1
    },
    // Precise timestamp within the session
    timestamp: {
        type: Date,
        required: true,
        index: true
    },
    // Offset from session start in milliseconds
    sessionOffset: {
        type: Number,
        required: true
    },
    // Bounding box at time of event (for snippet alignment)
    boundingBox: {
        x: Number,
        y: Number,
        width: Number,
        height: Number
    },
    // Additional event-specific data
    data: {
        // For attention events
        gazeDirection: {
            yaw: Number,
            pitch: Number
        },
        // For posture events
        postureScore: Number,
        // For phone detection
        phoneConfidence: Number,
        // For emotion-related events
        emotion: String,
        emotionConfidence: Number,
        // Face matching confidence (if student identified)
        matchConfidence: Number
    },
    // Reference to video snippet (if captured)
    snippet: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Snippet',
        sparse: true
    },
    // Processing metadata
    processed: {
        type: Boolean,
        default: false
    },
    processedAt: Date
}, {
    timestamps: true
});

// Compound indexes for efficient queries
eventSchema.index({ session: 1, timestamp: 1 });
eventSchema.index({ session: 1, eventType: 1 });
eventSchema.index({ session: 1, trackId: 1, timestamp: 1 });
eventSchema.index({ student: 1, timestamp: -1 });

// Static method to get events for a session
eventSchema.statics.findBySession = function(sessionId, options = {}) {
    const query = { session: sessionId };
    
    if (options.eventTypes && options.eventTypes.length > 0) {
        query.eventType = { $in: options.eventTypes };
    }
    
    if (options.trackId) {
        query.trackId = options.trackId;
    }
    
    if (options.student) {
        query.student = options.student;
    }
    
    if (options.startTime || options.endTime) {
        query.timestamp = {};
        if (options.startTime) query.timestamp.$gte = options.startTime;
        if (options.endTime) query.timestamp.$lte = options.endTime;
    }
    
    return this.find(query)
        .sort({ timestamp: 1 })
        .limit(options.limit || 1000)
        .populate('student', 'studentId name')
        .populate('snippet', 'filename duration');
};

// Static method to aggregate events by type for a session
eventSchema.statics.aggregateByType = async function(sessionId) {
    return await this.aggregate([
        { $match: { session: new mongoose.Types.ObjectId(sessionId) } },
        {
            $group: {
                _id: '$eventType',
                count: { $sum: 1 },
                avgConfidence: { $avg: '$confidence' },
                firstOccurrence: { $min: '$timestamp' },
                lastOccurrence: { $max: '$timestamp' }
            }
        },
        { $sort: { count: -1 } }
    ]);
};

// Static method to get timeline data for visualization
eventSchema.statics.getTimeline = async function(sessionId, intervalMs = 60000) {
    const events = await this.find({ session: sessionId })
        .sort({ timestamp: 1 })
        .select('timestamp eventType confidence')
        .lean();
    
    if (events.length === 0) return [];
    
    const startTime = events[0].timestamp.getTime();
    const endTime = events[events.length - 1].timestamp.getTime();
    const timeline = [];
    
    for (let t = startTime; t <= endTime; t += intervalMs) {
        const intervalEvents = events.filter(e => {
            const et = e.timestamp.getTime();
            return et >= t && et < t + intervalMs;
        });
        
        const attentionEvents = intervalEvents.filter(e => 
            e.eventType.includes('attention')
        );
        
        const distractionEvents = intervalEvents.filter(e => 
            ['phone_detected', 'distraction', 'attention_low', 'attention_lost']
                .includes(e.eventType)
        );
        
        timeline.push({
            time: new Date(t),
            totalEvents: intervalEvents.length,
            attentionScore: attentionEvents.length > 0 
                ? attentionEvents.filter(e => e.eventType === 'attention_high').length / attentionEvents.length 
                : null,
            distractionCount: distractionEvents.length
        });
    }
    
    return timeline;
};

const Event = mongoose.model('Event', eventSchema);

module.exports = Event;
