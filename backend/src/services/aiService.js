/**
 * AI Service Client
 * Handles communication with Python AI microservice
 */

const axios = require('axios');
const config = require('../config');
const logger = require('../utils/logger');

class AIServiceClient {
    constructor() {
        this.baseUrl = config.aiService.url;
        this.timeout = config.aiService.timeout;
        this.client = axios.create({
            baseURL: this.baseUrl,
            timeout: this.timeout,
            headers: {
                'Content-Type': 'application/json'
            }
        });

        // Request interceptor for logging
        this.client.interceptors.request.use(
            (config) => {
                logger.debug(`AI Service Request: ${config.method?.toUpperCase()} ${config.url}`);
                return config;
            },
            (error) => {
                logger.error('AI Service Request Error:', error);
                return Promise.reject(error);
            }
        );

        // Response interceptor for logging
        this.client.interceptors.response.use(
            (response) => {
                logger.debug(`AI Service Response: ${response.status} ${response.config.url}`);
                return response;
            },
            (error) => {
                logger.error('AI Service Response Error:', error.message);
                return Promise.reject(error);
            }
        );
    }

    /**
     * Check AI service health
     */
    async healthCheck() {
        try {
            const response = await this.client.get('/health');
            return {
                healthy: true,
                data: response.data
            };
        } catch (error) {
            return {
                healthy: false,
                error: error.message
            };
        }
    }

    /**
     * Process enrollment image
     */
    async processEnrollmentImage(studentId, imageData, captureIndex) {
        try {
            const response = await this.client.post('/api/enrollment/capture', {
                studentId,
                imageData,
                captureIndex
            });
            return response.data;
        } catch (error) {
            logger.error('Enrollment capture error:', error.message);
            throw new Error('Failed to process enrollment image');
        }
    }

    /**
     * Complete enrollment and get averaged embedding
     */
    async completeEnrollment(studentId) {
        try {
            const response = await this.client.post('/api/enrollment/complete', {
                studentId
            }, { timeout: 60000 });
            return response.data;
        } catch (error) {
            logger.error('Enrollment completion error:', error.message);
            throw new Error('Failed to complete enrollment');
        }
    }

    /**
     * Reset enrollment captures
     */
    async resetEnrollment(studentId) {
        try {
            const response = await this.client.post('/api/enrollment/reset', {
                studentId
            });
            return response.data;
        } catch (error) {
            logger.error('Enrollment reset error:', error.message);
            throw new Error('Failed to reset enrollment');
        }
    }

    /**
     * Start monitoring session
     */
    async startSession(sessionId, cameraConfig, expectedDuration) {
        try {
            const response = await this.client.post('/api/session/start', {
                sessionId,
                camera: cameraConfig,
                expectedDuration
            });
            return response.data;
        } catch (error) {
            logger.error('Session start error:', error.message);
            throw new Error('Failed to start AI monitoring session');
        }
    }

    /**
     * Stop monitoring session
     */
    async stopSession(sessionId) {
        try {
            const response = await this.client.post('/api/session/stop', {
                sessionId
            });
            return response.data;
        } catch (error) {
            logger.error('Session stop error:', error.message);
            throw new Error('Failed to stop AI monitoring session');
        }
    }

    /**
     * Get session analytics
     */
    async getSessionAnalytics(sessionId) {
        try {
            const response = await this.client.get(`/api/session/${sessionId}/analytics`);
            return response.data;
        } catch (error) {
            logger.error('Get analytics error:', error.message);
            throw new Error('Failed to get session analytics');
        }
    }

    /**
     * Match face embedding against known students
     */
    async matchEmbedding(embedding, threshold = 0.5) {
        try {
            const response = await this.client.post('/api/recognition/match', {
                embedding,
                threshold
            });
            return response.data;
        } catch (error) {
            logger.error('Embedding match error:', error.message);
            throw new Error('Failed to match embedding');
        }
    }

    /**
     * Get available camera devices
     */
    async getCameras() {
        try {
            const response = await this.client.get('/api/cameras');
            return response.data;
        } catch (error) {
            logger.error('Get cameras error:', error.message);
            throw new Error('Failed to get camera list');
        }
    }

    /**
     * Get model status
     */
    async getModelStatus() {
        try {
            const response = await this.client.get('/api/models/status');
            return response.data;
        } catch (error) {
            logger.error('Get model status error:', error.message);
            throw new Error('Failed to get model status');
        }
    }
}

// Singleton instance
const aiServiceClient = new AIServiceClient();

module.exports = aiServiceClient;
