/**
 * Embedding Model
 * Stores face embeddings for student recognition
 * Raw images are NOT stored - only averaged embeddings
 */

const mongoose = require('mongoose');

const embeddingSchema = new mongoose.Schema({
    studentId: {
        type: mongoose.Schema.Types.ObjectId,
        ref: 'Student',
        required: true,
        unique: true
    },
    // Averaged face embedding vector (512-dimensional for ArcFace/InsightFace)
    embedding: {
        type: [Number],
        required: true,
        validate: {
            validator: function(arr) {
                // ArcFace embeddings are typically 512-dimensional
                return arr.length === 512;
            },
            message: 'Embedding must be 512-dimensional'
        }
    },
    // Metadata about the embedding quality
    quality: {
        averageConfidence: {
            type: Number,
            min: 0,
            max: 1
        },
        imagesUsed: {
            type: Number,
            min: 1
        },
        // Standard deviation across captured embeddings (lower = more consistent)
        consistency: {
            type: Number,
            min: 0
        }
    },
    // Model information for reproducibility
    modelInfo: {
        name: {
            type: String,
            default: 'buffalo_l' // InsightFace model
        },
        version: String,
        backendVersion: String
    },
    // L2-normalized flag (embeddings should be normalized for cosine similarity)
    isNormalized: {
        type: Boolean,
        default: true
    },
    // Last verification date (when embedding was last used successfully)
    lastVerified: {
        type: Date
    },
    // Count of successful recognitions
    recognitionCount: {
        type: Number,
        default: 0
    }
}, {
    timestamps: true
});

// Index for efficient lookup
embeddingSchema.index({ studentId: 1 });
embeddingSchema.index({ createdAt: -1 });

// Method to increment recognition count
embeddingSchema.methods.recordRecognition = async function() {
    this.recognitionCount += 1;
    this.lastVerified = new Date();
    return await this.save();
};

// Static method to get all embeddings for matching
embeddingSchema.statics.getAllForMatching = async function() {
    return await this.find()
        .populate('studentId', 'studentId name')
        .select('embedding studentId quality.averageConfidence')
        .lean();
};

// Static method to compute cosine similarity
embeddingSchema.statics.cosineSimilarity = function(embedding1, embedding2) {
    if (embedding1.length !== embedding2.length) {
        throw new Error('Embeddings must have the same dimension');
    }
    
    let dotProduct = 0;
    let norm1 = 0;
    let norm2 = 0;
    
    for (let i = 0; i < embedding1.length; i++) {
        dotProduct += embedding1[i] * embedding2[i];
        norm1 += embedding1[i] * embedding1[i];
        norm2 += embedding2[i] * embedding2[i];
    }
    
    norm1 = Math.sqrt(norm1);
    norm2 = Math.sqrt(norm2);
    
    if (norm1 === 0 || norm2 === 0) return 0;
    
    return dotProduct / (norm1 * norm2);
};

const Embedding = mongoose.model('Embedding', embeddingSchema);

module.exports = Embedding;
