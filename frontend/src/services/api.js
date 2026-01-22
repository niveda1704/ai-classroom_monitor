/**
 * API Service
 * Handles all HTTP requests to the backend
 */

const API_BASE_URL = '/api';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('auth_token');
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      // Handle empty responses
      const text = await response.text();
      let data = {};
      
      if (text) {
        try {
          data = JSON.parse(text);
        } catch (parseError) {
          console.error('JSON parse error:', parseError);
          if (!response.ok) {
            throw new Error('Server error');
          }
          return { success: true };
        }
      }

      if (!response.ok) {
        throw new Error(data.error || 'Request failed');
      }

      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }

  // Auth endpoints
  async login(email, password) {
    const data = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (data.data?.token) {
      this.setToken(data.data.token);
    }
    return data;
  }

  async register(userData) {
    const data = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
    if (data.data?.token) {
      this.setToken(data.data.token);
    }
    return data;
  }

  async getProfile() {
    return this.request('/auth/me');
  }

  async logout() {
    this.setToken(null);
  }

  // Student endpoints
  async getStudents(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/students?${query}`);
  }

  async createStudent(studentData) {
    return this.request('/students', {
      method: 'POST',
      body: JSON.stringify(studentData),
    });
  }

  async getStudent(id) {
    return this.request(`/students/${id}`);
  }

  async updateStudent(id, data) {
    return this.request(`/students/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteStudent(id) {
    return this.request(`/students/${id}`, {
      method: 'DELETE',
    });
  }

  async startEnrollment(studentId, requiredImages = 15) {
    return this.request(`/students/${studentId}/enrollment/start`, {
      method: 'POST',
      body: JSON.stringify({ requiredImages }),
    });
  }

  async captureEnrollment(studentId, imageData) {
    return this.request(`/students/${studentId}/enrollment/capture`, {
      method: 'POST',
      body: JSON.stringify({ imageData }),
    });
  }

  async completeEnrollment(studentId) {
    return this.request(`/students/${studentId}/enrollment/complete`, {
      method: 'POST',
    });
  }

  async resetEnrollment(studentId) {
    return this.request(`/students/${studentId}/enrollment/reset`, {
      method: 'POST',
    });
  }

  // Session endpoints
  async getSessions(params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/sessions?${query}`);
  }

  async createSession(sessionData) {
    return this.request('/sessions', {
      method: 'POST',
      body: JSON.stringify(sessionData),
    });
  }

  async getSession(id) {
    return this.request(`/sessions/${id}`);
  }

  async startSession(id) {
    return this.request(`/sessions/${id}/start`, {
      method: 'POST',
    });
  }

  async pauseSession(id) {
    return this.request(`/sessions/${id}/pause`, {
      method: 'POST',
    });
  }

  async resumeSession(id) {
    return this.request(`/sessions/${id}/resume`, {
      method: 'POST',
    });
  }

  async completeSession(id) {
    return this.request(`/sessions/${id}/complete`, {
      method: 'POST',
    });
  }

  async getSessionAnalytics(id) {
    return this.request(`/sessions/${id}/analytics`);
  }

  async getSessionStudents(id) {
    return this.request(`/sessions/${id}/students`);
  }

  async getSessionEvents(id, params = {}) {
    const query = new URLSearchParams(params).toString();
    return this.request(`/sessions/${id}/events?${query}`);
  }

  async downloadReport(id, format = 'json') {
    return this.request(`/sessions/${id}/report?format=${format}`);
  }

  async deleteSession(id) {
    return this.request(`/sessions/${id}`, {
      method: 'DELETE',
    });
  }

  // AI Processing endpoints
  async processFrame(sessionId, imageData) {
    return this.request(`/sessions/${sessionId}/process-frame`, {
      method: 'POST',
      body: JSON.stringify({ imageData, timestamp: new Date().toISOString() }),
    });
  }
}

export const api = new ApiService();
export default api;
