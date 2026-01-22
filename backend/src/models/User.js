/**
 * User Model
 * Handles faculty and admin authentication
 */

const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
    email: {
        type: String,
        required: [true, 'Email is required'],
        unique: true,
        lowercase: true,
        trim: true,
        match: [/^\S+@\S+\.\S+$/, 'Please provide a valid email']
    },
    password: {
        type: String,
        required: [true, 'Password is required'],
        minlength: [8, 'Password must be at least 8 characters'],
        select: false // Don't include password in queries by default
    },
    name: {
        type: String,
        required: [true, 'Name is required'],
        trim: true,
        maxlength: [100, 'Name cannot exceed 100 characters']
    },
    role: {
        type: String,
        enum: ['faculty', 'admin'],
        default: 'faculty'
    },
    department: {
        type: String,
        trim: true
    },
    isActive: {
        type: Boolean,
        default: true
    },
    lastLogin: {
        type: Date
    },
    passwordChangedAt: {
        type: Date
    },
    refreshTokens: [{
        token: String,
        createdAt: {
            type: Date,
            default: Date.now,
            expires: 604800 // 7 days in seconds
        }
    }]
}, {
    timestamps: true
});

// Index for faster queries
userSchema.index({ email: 1 });
userSchema.index({ role: 1, isActive: 1 });

// Hash password before saving
userSchema.pre('save', async function(next) {
    if (!this.isModified('password')) return next();
    
    try {
        const salt = await bcrypt.genSalt(12);
        this.password = await bcrypt.hash(this.password, salt);
        this.passwordChangedAt = Date.now() - 1000; // Ensure token created after password
        next();
    } catch (error) {
        next(error);
    }
});

// Compare password method
userSchema.methods.comparePassword = async function(candidatePassword) {
    return await bcrypt.compare(candidatePassword, this.password);
};

// Check if password changed after token was issued
userSchema.methods.changedPasswordAfter = function(tokenIssuedAt) {
    if (this.passwordChangedAt) {
        const changedTimestamp = parseInt(this.passwordChangedAt.getTime() / 1000, 10);
        return tokenIssuedAt < changedTimestamp;
    }
    return false;
};

// Update last login
userSchema.methods.updateLastLogin = async function() {
    this.lastLogin = new Date();
    await this.save({ validateBeforeSave: false });
};

// Static method to find active users by role
userSchema.statics.findActiveByRole = function(role) {
    return this.find({ role, isActive: true });
};

const User = mongoose.model('User', userSchema);

module.exports = User;
