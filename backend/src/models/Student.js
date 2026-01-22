/**
 * Student Model
 * Stores student information and links to face embeddings
 */

const mongoose = require('mongoose');

const studentSchema = new mongoose.Schema({
    studentId: {
        type: String,
        required: [true, 'Student ID is required'],
        unique: true,
        trim: true,
        uppercase: true
    },
    name: {
        type: String,
        required: [true, 'Student name is required'],
        trim: true,
        maxlength: [100, 'Name cannot exceed 100 characters']
    },
    email: {
        type: String,
        lowercase: true,
        trim: true,
        sparse: true // Allow null but unique when present
    },
    enrolledBy: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'User',
        required: true
    },
    enrollmentDate: {
        type: Date,
        default: Date.now
    },
    isActive: {
        type: Boolean,
        default: true
    },
    metadata: {
        department: String,
        batch: String,
        section: String
    },
    // Reference to the embedding document
    embeddingId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Embedding'
    },
    // Enrollment status tracking
    enrollmentStatus: {
        type: String,
        enum: ['pending', 'capturing', 'processing', 'completed', 'failed'],
        default: 'pending'
    },
    enrollmentProgress: {
        capturedImages: {
            type: Number,
            default: 0
        },
        requiredImages: {
            type: Number,
            default: 15
        }
    }
}, {
    timestamps: true
});

// Indexes
studentSchema.index({ studentId: 1 });
studentSchema.index({ enrolledBy: 1 });
studentSchema.index({ 'metadata.department': 1, 'metadata.batch': 1 });
studentSchema.index({ isActive: 1, enrollmentStatus: 1 });

// Virtual for enrollment completion percentage
studentSchema.virtual('enrollmentCompletion').get(function() {
    const { capturedImages, requiredImages } = this.enrollmentProgress;
    return Math.round((capturedImages / requiredImages) * 100);
});

// Ensure virtuals are included in JSON
studentSchema.set('toJSON', { virtuals: true });
studentSchema.set('toObject', { virtuals: true });

// Static method to find students by faculty
studentSchema.statics.findByFaculty = function(facultyId) {
    return this.find({ enrolledBy: facultyId, isActive: true })
        .populate('embeddingId', 'quality createdAt')
        .sort({ name: 1 });
};

// Instance method to update enrollment progress
studentSchema.methods.updateEnrollmentProgress = async function(capturedCount) {
    this.enrollmentProgress.capturedImages = capturedCount;
    
    if (capturedCount >= this.enrollmentProgress.requiredImages) {
        this.enrollmentStatus = 'processing';
    } else if (capturedCount > 0) {
        this.enrollmentStatus = 'capturing';
    }
    
    return await this.save();
};

const Student = mongoose.model('Student', studentSchema);

module.exports = Student;
