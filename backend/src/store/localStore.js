/**
 * Local File-Based Data Store
 * Stores all data in JSON files locally - no database needed!
 * Data persists between restarts and has zero network latency
 */

const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');

// Data directory
const DATA_DIR = path.join(__dirname, '../../data');

// Ensure data directory exists
if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

// File paths
const FILES = {
  users: path.join(DATA_DIR, 'users.json'),
  students: path.join(DATA_DIR, 'students.json'),
  sessions: path.join(DATA_DIR, 'sessions.json'),
  events: path.join(DATA_DIR, 'events.json'),
  embeddings: path.join(DATA_DIR, 'embeddings.json'),
};

// ===== File Utilities =====

const readJSON = (filePath) => {
  try {
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error(`Error reading ${filePath}:`, err.message);
  }
  return [];
};

const writeJSON = (filePath, data) => {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
  } catch (err) {
    console.error(`Error writing ${filePath}:`, err.message);
  }
};

// Helper to generate IDs
const generateId = () => {
  return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
};

// ===== In-Memory Cache (loaded from files) =====

const store = {
  users: readJSON(FILES.users),
  students: readJSON(FILES.students),
  sessions: readJSON(FILES.sessions),
  events: readJSON(FILES.events),
  embeddings: readJSON(FILES.embeddings),
};

// Save functions (debounced for performance)
let saveTimeouts = {};

const saveToFile = (key) => {
  // Debounce saves - wait 500ms after last change
  if (saveTimeouts[key]) {
    clearTimeout(saveTimeouts[key]);
  }
  saveTimeouts[key] = setTimeout(() => {
    writeJSON(FILES[key], store[key]);
    console.log(`💾 Saved ${key} to local storage (${store[key].length} records)`);
  }, 500);
};

const saveImmediate = (key) => {
  writeJSON(FILES[key], store[key]);
};

// ===== Initialize Default Data =====

const initializeDefaultData = async () => {
  // Create default user if none exist
  if (store.users.length === 0) {
    const hashedPassword = await bcrypt.hash('abcd', 8);
    store.users.push({
      _id: 'default-user-001',
      name: 'Instructor',
      email: '123@gmail.com',
      password: hashedPassword,
      role: 'faculty',
      department: 'Computer Science',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    });
    saveImmediate('users');
    console.log('👤 Created default user: 123@gmail.com / abcd');
  }
};

// Initialize on load
initializeDefaultData();

// ===== User Operations =====

const userStore = {
  async create(userData) {
    const hashedPassword = await bcrypt.hash(userData.password, 8);
    const user = {
      _id: generateId(),
      name: userData.name,
      email: userData.email.toLowerCase(),
      password: hashedPassword,
      role: userData.role || 'faculty',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    store.users.push(user);
    saveToFile('users');
    return { ...user, password: undefined };
  },

  async findByEmail(email) {
    return store.users.find(u => u.email === email.toLowerCase());
  },

  async findById(id) {
    const user = store.users.find(u => u._id === id);
    if (user) {
      return { ...user, password: undefined };
    }
    return null;
  },

  async comparePassword(user, password) {
    const fullUser = store.users.find(u => u._id === user._id);
    if (!fullUser) return false;
    return bcrypt.compare(password, fullUser.password);
  },

  async updatePassword(userId, newPassword) {
    const user = store.users.find(u => u._id === userId);
    if (user) {
      user.password = await bcrypt.hash(newPassword, 8);
      user.updatedAt = new Date().toISOString();
      saveToFile('users');
    }
    return user;
  },
};

// ===== Student Operations =====

const studentStore = {
  async create(studentData) {
    const student = {
      _id: generateId(),
      studentId: studentData.studentId,
      name: studentData.name,
      email: studentData.email || '',
      course: studentData.course || '',
      department: studentData.department || '',
      enrollmentStatus: 'not_enrolled',
      createdBy: studentData.createdBy,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    store.students.push(student);
    saveToFile('students');
    return student;
  },

  async findById(id) {
    return store.students.find(s => s._id === id);
  },

  async findByStudentId(studentId) {
    return store.students.find(s => s.studentId === studentId);
  },

  async findAll(query = {}) {
    let results = [...store.students];
    
    if (query.enrollmentStatus) {
      results = results.filter(s => s.enrollmentStatus === query.enrollmentStatus);
    }
    if (query.search) {
      const search = query.search.toLowerCase();
      results = results.filter(s => 
        s.name.toLowerCase().includes(search) ||
        s.studentId.toLowerCase().includes(search) ||
        (s.email && s.email.toLowerCase().includes(search))
      );
    }
    
    // Sort
    results.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));
    
    // Pagination
    const skip = query.skip || 0;
    const limit = query.limit || 50;
    
    return {
      students: results.slice(skip, skip + limit),
      total: results.length,
    };
  },

  async update(id, data) {
    const index = store.students.findIndex(s => s._id === id);
    if (index !== -1) {
      store.students[index] = {
        ...store.students[index],
        ...data,
        updatedAt: new Date().toISOString(),
      };
      saveToFile('students');
      return store.students[index];
    }
    return null;
  },

  async delete(id) {
    const index = store.students.findIndex(s => s._id === id);
    if (index !== -1) {
      store.students.splice(index, 1);
      // Also delete embeddings
      store.embeddings = store.embeddings.filter(e => e.studentId !== id);
      saveToFile('students');
      saveToFile('embeddings');
      return true;
    }
    return false;
  },
};

// ===== Session Operations =====

const sessionStore = {
  async create(sessionData) {
    const session = {
      _id: generateId(),
      name: sessionData.name,
      courseName: sessionData.courseName,
      roomNumber: sessionData.roomNumber || '',
      description: sessionData.description || '',
      status: 'created',
      createdBy: sessionData.createdBy,
      startedAt: null,
      completedAt: null,
      pausedDuration: 0,
      actualDuration: 0,
      liveMetrics: {
        totalDetected: 0,
        identifiedCount: 0,
        avgAttention: 0,
        phoneCount: 0,
        postureAlerts: 0,
      },
      finalAnalytics: null,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    store.sessions.push(session);
    saveToFile('sessions');
    return session;
  },

  async findById(id) {
    return store.sessions.find(s => s._id === id);
  },

  async findAll(query = {}) {
    let results = [...store.sessions];
    
    if (query.status) {
      results = results.filter(s => s.status === query.status);
    }
    if (query.createdBy) {
      results = results.filter(s => s.createdBy === query.createdBy);
    }
    
    // Sort
    const sortField = query.sortBy || 'createdAt';
    const sortOrder = query.sortOrder === 'asc' ? 1 : -1;
    results.sort((a, b) => {
      if (a[sortField] < b[sortField]) return -sortOrder;
      if (a[sortField] > b[sortField]) return sortOrder;
      return 0;
    });
    
    // Pagination
    const skip = query.skip || 0;
    const limit = query.limit || 50;
    
    return {
      sessions: results.slice(skip, skip + limit),
      total: results.length,
    };
  },

  async update(id, data) {
    const index = store.sessions.findIndex(s => s._id === id);
    if (index !== -1) {
      store.sessions[index] = {
        ...store.sessions[index],
        ...data,
        updatedAt: new Date().toISOString(),
      };
      saveToFile('sessions');
      return store.sessions[index];
    }
    return null;
  },

  async delete(id) {
    const index = store.sessions.findIndex(s => s._id === id);
    if (index !== -1) {
      store.sessions.splice(index, 1);
      // Also delete events
      store.events = store.events.filter(e => e.sessionId !== id);
      saveToFile('sessions');
      saveToFile('events');
      return true;
    }
    return false;
  },
};

// ===== Event Operations =====

const eventStore = {
  async create(eventData) {
    const event = {
      _id: generateId(),
      sessionId: eventData.sessionId,
      studentId: eventData.studentId || null,
      trackId: eventData.trackId || null,
      eventType: eventData.eventType,
      details: eventData.details || {},
      confidence: eventData.confidence || 1.0,
      timestamp: eventData.timestamp || new Date().toISOString(),
      frameNumber: eventData.frameNumber || null,
      createdAt: new Date().toISOString(),
    };
    store.events.push(event);
    saveToFile('events');
    return event;
  },

  async createBatch(events) {
    const created = events.map(eventData => ({
      _id: generateId(),
      sessionId: eventData.sessionId,
      studentId: eventData.studentId || null,
      trackId: eventData.trackId || null,
      eventType: eventData.eventType,
      details: eventData.details || {},
      confidence: eventData.confidence || 1.0,
      timestamp: eventData.timestamp || new Date().toISOString(),
      frameNumber: eventData.frameNumber || null,
      createdAt: new Date().toISOString(),
    }));
    store.events.push(...created);
    saveToFile('events');
    return created;
  },

  async findBySession(sessionId, query = {}) {
    let results = store.events.filter(e => e.sessionId === sessionId);
    
    if (query.eventType) {
      results = results.filter(e => e.eventType === query.eventType);
    }
    if (query.studentId) {
      results = results.filter(e => e.studentId === query.studentId);
    }
    
    // Sort by timestamp
    results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
    
    // Pagination
    const skip = query.skip || 0;
    const limit = query.limit || 100;
    
    return {
      events: results.slice(skip, skip + limit),
      total: results.length,
    };
  },

  async getSessionSummary(sessionId) {
    const events = store.events.filter(e => e.sessionId === sessionId);
    
    const summary = {
      total: events.length,
      byType: {},
    };
    
    events.forEach(e => {
      summary.byType[e.eventType] = (summary.byType[e.eventType] || 0) + 1;
    });
    
    return summary;
  },
};

// ===== Embedding Operations =====

const embeddingStore = {
  async create(embeddingData) {
    const embedding = {
      _id: generateId(),
      studentId: embeddingData.studentId,
      embedding: embeddingData.embedding,
      isTemp: embeddingData.isTemp || false,
      createdAt: new Date().toISOString(),
    };
    store.embeddings.push(embedding);
    saveToFile('embeddings');
    return embedding;
  },

  async findByStudent(studentId, isTemp = false) {
    return store.embeddings.filter(e => e.studentId === studentId && e.isTemp === isTemp);
  },

  async deleteTempByStudent(studentId) {
    store.embeddings = store.embeddings.filter(e => !(e.studentId === studentId && e.isTemp));
    saveToFile('embeddings');
  },

  async convertTempToPermanent(studentId) {
    store.embeddings.forEach(e => {
      if (e.studentId === studentId && e.isTemp) {
        e.isTemp = false;
      }
    });
    saveToFile('embeddings');
  },

  async deleteByStudent(studentId) {
    store.embeddings = store.embeddings.filter(e => e.studentId !== studentId);
    saveToFile('embeddings');
  },

  async getAllPermanent() {
    return store.embeddings.filter(e => !e.isTemp);
  },
};

// ===== Export =====

module.exports = {
  store,
  userStore,
  studentStore,
  sessionStore,
  eventStore,
  embeddingStore,
  generateId,
  saveImmediate,
  DATA_DIR,
};
