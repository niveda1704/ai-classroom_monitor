/**
 * Local File-Based Data Store
 * All data is stored in JSON files locally for zero latency
 * Re-exports from localStore.js for backward compatibility
 */

// Use the local file-based store
const localStore = require('./localStore');

console.log('📁 Using LOCAL FILE STORAGE - Data saved to backend/data/');

// Export all stores from localStore
module.exports = localStore;
