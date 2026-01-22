/**
 * Snippet Model
 * Stores short video clips for event evidence
 * Only captures snippets when significant events occur (not continuous)
 */

const mongoose = require('mongoose');
const path = require('path');

const snippetSchema = new mongoose.Schema({
    session: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Session',
        required: true,
        index: true
    },
    // File information
    filename: {
        type: String,
        required: true,
        unique: true
    },
    filePath: {
        type: String,
        required: true
    },
    // Snippet timing
    startTime: {
        type: Date,
        required: true
    },
    endTime: {
        type: Date,
        required: true
    },
    duration: {
        type: Number, // Duration in seconds
        required: true,
        max: 30 // Maximum 30 seconds per snippet
    },
    // Session timeline offset
    sessionOffsetStart: {
        type: Number,
        required: true
    },
    sessionOffsetEnd: {
        type: Number,
        required: true
    },
    // File metadata
    fileSize: {
        type: Number, // Size in bytes
        required: true
    },
    format: {
        type: String,
        enum: ['mp4', 'webm'],
        default: 'mp4'
    },
    resolution: {
        width: Number,
        height: Number
    },
    frameRate: Number,
    // Trigger event (what caused this snippet to be captured)
    triggerEvent: {
        eventType: String,
        trackId: Number,
        confidence: Number
    },
    // Related events within this snippet
    relatedEvents: [{
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Event'
    }],
    // Thumbnail for preview
    thumbnail: {
        filename: String,
        filePath: String
    },
    // Retention policy
    expiresAt: {
        type: Date,
        index: { expireAfterSeconds: 0 } // TTL index
    },
    // Access tracking
    accessCount: {
        type: Number,
        default: 0
    },
    lastAccessedAt: Date
}, {
    timestamps: true
});

// Indexes
snippetSchema.index({ session: 1, startTime: 1 });
snippetSchema.index({ 'triggerEvent.eventType': 1 });

// Virtual for human-readable file size
snippetSchema.virtual('fileSizeFormatted').get(function() {
    const kb = this.fileSize / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(2)} MB`;
});

snippetSchema.set('toJSON', { virtuals: true });
snippetSchema.set('toObject', { virtuals: true });

// Record access
snippetSchema.methods.recordAccess = async function() {
    this.accessCount += 1;
    this.lastAccessedAt = new Date();
    return await this.save();
};

// Static method to get snippets for a session
snippetSchema.statics.findBySession = function(sessionId, options = {}) {
    const query = { session: sessionId };
    
    if (options.eventType) {
        query['triggerEvent.eventType'] = options.eventType;
    }
    
    return this.find(query)
        .sort({ startTime: 1 })
        .select('-filePath') // Don't expose internal paths
        .limit(options.limit || 100);
};

// Static method to calculate total storage used by a session
snippetSchema.statics.getStorageBySession = async function(sessionId) {
    const result = await this.aggregate([
        { $match: { session: new mongoose.Types.ObjectId(sessionId) } },
        {
            $group: {
                _id: null,
                totalSize: { $sum: '$fileSize' },
                count: { $sum: 1 },
                totalDuration: { $sum: '$duration' }
            }
        }
    ]);
    
    return result[0] || { totalSize: 0, count: 0, totalDuration: 0 };
};

// Pre-save: Set default expiration (30 days)
snippetSchema.pre('save', function(next) {
    if (this.isNew && !this.expiresAt) {
        const thirtyDays = 30 * 24 * 60 * 60 * 1000;
        this.expiresAt = new Date(Date.now() + thirtyDays);
    }
    next();
});

const Snippet = mongoose.model('Snippet', snippetSchema);

module.exports = Snippet;
