/**
 * Routes Index
 * Export all route modules
 * Using in-memory storage version for demo mode
 */

const authRoutes = require('./auth.memory');
const studentRoutes = require('./students.memory');
const sessionRoutes = require('./sessions.memory');
const eventRoutes = require('./events.memory');

module.exports = {
    authRoutes,
    studentRoutes,
    sessionRoutes,
    eventRoutes
};
