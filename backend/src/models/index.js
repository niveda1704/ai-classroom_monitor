/**
 * Model Index
 * Export all MongoDB models
 */

const User = require('./User');
const Student = require('./Student');
const Embedding = require('./Embedding');
const Session = require('./Session');
const Event = require('./Event');
const Snippet = require('./Snippet');

module.exports = {
    User,
    Student,
    Embedding,
    Session,
    Event,
    Snippet
};
