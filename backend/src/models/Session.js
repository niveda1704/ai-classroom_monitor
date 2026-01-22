/**
 * Session Model
 * Manages classroom monitoring sessions
 */

const mongoose = require('mongoose');

const sessionSchema = new mongoose.Schema({
    name: {
        type: String,
        required: [true, 'Session name is required'],
        trim: true,
        maxlength: [200, 'Session name cannot exceed 200 characters']
    },
    faculty: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    // Session timing
    expectedDuration: {
        type: Number, // Duration in minutes
        required: true,
        min: [5, 'Session must be at least 5 minutes'],
        max: [480, 'Session cannot exceed 8 hours']
    },
    actualStartTime: {
        type: Date
    },
    actualEndTime: {
        type: Date
    },
    // Session state machine
    status: {
        type: String,
        enum: ['created', 'running', 'paused', 'completed', 'cancelled'],
        default: 'created'
    },
    // Camera configuration (single camera only)
    camera: {
        deviceId: {
            type: String,
            required: true
        },
        label: String,
        resolution: {
            width: Number,
            height: Number
        }
    },
    // Real-time metrics (updated during session)
    liveMetrics: {
        currentStudentCount: {
            type: Number,
            default: 0
        },
        averageAttention: {
            type: Number,
            default: 0
        },
        lastUpdateTime: Date
    },
    // Final analytics (computed when session ends)
    analytics: {
        totalDuration: Number, // Actual duration in seconds
        averageStudentCount: Number,
        peakStudentCount: Number,
        // Aggregated attention metrics
        attention: {
            average: Number,
            min: Number,
            max: Number,
            timeline: [{
                timestamp: Date,
                value: Number
            }]
        },
        // Engagement metrics
        engagement: {
            average: Number,
            timeline: [{
                timestamp: Date,
                value: Number
            }]
        },
        // Distraction summary
        distraction: {
            totalTime: Number, // Seconds
            phoneUsageEvents: Number,
            lookingAwayEvents: Number
        },
        // Per-student analytics
        studentMetrics: [{
            studentId: {
                type: mongoose.Schema.Types.ObjectId,
                ref: 'Student'
            },
            name: String,
            attendancePercentage: Number,
            averageAttention: Number,
            distractionCount: Number,
            phoneUsageCount: Number,
            firstSeen: Date,
            lastSeen: Date,
            totalTimePresent: Number // Seconds
        }]
    },
    // Metadata
    metadata: {
        course: String,
        className: String,
        room: String,
        notes: String
    },
    // Event summary counts (for quick reference)
    eventCounts: {
        total: { type: Number, default: 0 },
        attention: { type: Number, default: 0 },
        distraction: { type: Number, default: 0 },
        phoneUsage: { type: Number, default: 0 },
        posture: { type: Number, default: 0 }
    }
}, {
    timestamps: true
});

// Indexes
sessionSchema.index({ faculty: 1, status: 1 });
sessionSchema.index({ createdAt: -1 });
sessionSchema.index({ 'metadata.course': 1 });
sessionSchema.index({ status: 1, actualStartTime: -1 });

// Virtual for duration in human-readable format
sessionSchema.virtual('formattedDuration').get(function() {
    if (!this.actualStartTime || !this.actualEndTime) return null;
    const duration = this.actualEndTime - this.actualStartTime;
    const minutes = Math.floor(duration / 60000);
    const hours = Math.floor(minutes / 60);
    const mins = minutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
});

sessionSchema.set('toJSON', { virtuals: true });
sessionSchema.set('toObject', { virtuals: true });

// Start session
sessionSchema.methods.start = async function() {
    if (this.status !== 'created') {
        throw new Error('Session can only be started from created state');
    }
    this.status = 'running';
    this.actualStartTime = new Date();
    return await this.save();
};

// Pause session
sessionSchema.methods.pause = async function() {
    if (this.status !== 'running') {
        throw new Error('Session can only be paused from running state');
    }
    this.status = 'paused';
    return await this.save();
};

// Resume session
sessionSchema.methods.resume = async function() {
    if (this.status !== 'paused') {
        throw new Error('Session can only be resumed from paused state');
    }
    this.status = 'running';
    return await this.save();
};

// Complete session
sessionSchema.methods.complete = async function(finalAnalytics) {
    if (this.status !== 'running' && this.status !== 'paused') {
        throw new Error('Session can only be completed from running or paused state');
    }
    this.status = 'completed';
    this.actualEndTime = new Date();
    
    if (finalAnalytics) {
        this.analytics = finalAnalytics;
    }
    
    // Calculate total duration
    if (this.actualStartTime) {
        this.analytics.totalDuration = Math.floor(
            (this.actualEndTime - this.actualStartTime) / 1000
        );
    }
    
    return await this.save();
};

// Update live metrics
sessionSchema.methods.updateLiveMetrics = async function(metrics) {
    this.liveMetrics = {
        ...this.liveMetrics,
        ...metrics,
        lastUpdateTime: new Date()
    };
    return await this.save();
};

// Static method to get faculty's sessions
sessionSchema.statics.findByFaculty = function(facultyId, options = {}) {
    const query = { faculty: facultyId };
    
    if (options.status) {
        query.status = options.status;
    }
    
    return this.find(query)
        .sort({ createdAt: -1 })
        .limit(options.limit || 50);
};

const Session = mongoose.model('Session', sessionSchema);

module.exports = Session;
