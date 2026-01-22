import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import {
  Plus,
  Play,
  Pause,
  StopCircle,
  BarChart3,
  Trash2,
  Video,
  Clock,
  Users,
  X,
} from 'lucide-react';

function CreateSessionModal({ isOpen, onClose, onCreate }) {
  const [formData, setFormData] = useState({
    name: '',
    courseName: '',
    roomNumber: '',
    description: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      await onCreate(formData);
      setFormData({ name: '', courseName: '', roomNumber: '', description: '' });
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-gray-800 rounded-xl w-full max-w-md p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Create New Session</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="h-5 w-5" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400 text-sm">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Session Name *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., Lecture 1 - Introduction"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Course Name *
            </label>
            <input
              type="text"
              name="courseName"
              value={formData.courseName}
              onChange={handleChange}
              required
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., CS101 - Programming Fundamentals"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Room Number
            </label>
            <input
              type="text"
              name="roomNumber"
              value={formData.roomNumber}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="e.g., Room 101"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Description
            </label>
            <textarea
              name="description"
              value={formData.description}
              onChange={handleChange}
              rows={3}
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500 resize-none"
              placeholder="Optional description..."
            />
          </div>

          <div className="flex space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2.5 px-4 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 py-2.5 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-600/50 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-5 w-5 border-t-2 border-b-2 border-white"></div>
              ) : (
                'Create Session'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SessionCard({ session, onDelete, onStatusChange }) {
  const [loading, setLoading] = useState(false);

  const statusColors = {
    created: { bg: 'bg-gray-500', text: 'text-gray-100', label: 'Created' },
    running: { bg: 'bg-green-500', text: 'text-green-100', label: 'Running' },
    paused: { bg: 'bg-yellow-500', text: 'text-yellow-100', label: 'Paused' },
    completed: { bg: 'bg-blue-500', text: 'text-blue-100', label: 'Completed' },
  };

  const status = statusColors[session.status] || statusColors.created;

  const handleAction = async (action) => {
    setLoading(true);
    try {
      await onStatusChange(session._id, action);
    } catch (error) {
      console.error('Action failed:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this session?')) return;
    await onDelete(session._id);
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">{session.name}</h3>
          <p className="text-gray-400 text-sm mt-1">{session.courseName}</p>
        </div>
        <span
          className={`px-2.5 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}
        >
          {status.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="flex items-center space-x-2 text-gray-400 text-sm">
          <Clock className="h-4 w-4" />
          <span>{formatDuration(session.actualDuration)}</span>
        </div>
        <div className="flex items-center space-x-2 text-gray-400 text-sm">
          <Users className="h-4 w-4" />
          <span>{session.liveMetrics?.totalDetected || 0} students</span>
        </div>
        <div className="flex items-center space-x-2 text-gray-400 text-sm">
          <Video className="h-4 w-4" />
          <span>{session.roomNumber || 'No room'}</span>
        </div>
      </div>

      <div className="text-xs text-gray-500 mb-4">
        Created: {new Date(session.createdAt).toLocaleString()}
      </div>

      <div className="flex items-center space-x-2">
        {session.status === 'created' && (
          <>
            <Link
              to={`/sessions/${session._id}/monitor`}
              className="flex-1 py-2 px-4 bg-green-600 hover:bg-green-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              <Play className="h-4 w-4 mr-1" />
              Start
            </Link>
            <button
              onClick={handleDelete}
              className="p-2 text-red-400 hover:text-red-300 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </>
        )}

        {session.status === 'running' && (
          <>
            <Link
              to={`/sessions/${session._id}/monitor`}
              className="flex-1 py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              <Video className="h-4 w-4 mr-1" />
              Monitor
            </Link>
            <button
              onClick={() => handleAction('pause')}
              disabled={loading}
              className="p-2 text-yellow-400 hover:text-yellow-300 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Pause className="h-4 w-4" />
            </button>
            <button
              onClick={() => handleAction('complete')}
              disabled={loading}
              className="p-2 text-red-400 hover:text-red-300 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <StopCircle className="h-4 w-4" />
            </button>
          </>
        )}

        {session.status === 'paused' && (
          <>
            <button
              onClick={() => handleAction('resume')}
              disabled={loading}
              className="flex-1 py-2 px-4 bg-green-600 hover:bg-green-700 disabled:bg-green-600/50 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              <Play className="h-4 w-4 mr-1" />
              Resume
            </button>
            <button
              onClick={() => handleAction('complete')}
              disabled={loading}
              className="p-2 text-red-400 hover:text-red-300 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <StopCircle className="h-4 w-4" />
            </button>
          </>
        )}

        {session.status === 'completed' && (
          <>
            <Link
              to={`/sessions/${session._id}/analytics`}
              className="flex-1 py-2 px-4 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              <BarChart3 className="h-4 w-4 mr-1" />
              View Analytics
            </Link>
            <button
              onClick={handleDelete}
              className="p-2 text-red-400 hover:text-red-300 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </>
        )}
      </div>
    </div>
  );
}

function Sessions() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    setLoading(true);
    try {
      const response = await api.getSessions({ limit: 50, sortBy: 'createdAt', sortOrder: 'desc' });
      setSessions(response.data?.sessions || []);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSession = async (data) => {
    await api.createSession(data);
    await fetchSessions();
  };

  const handleDeleteSession = async (id) => {
    await api.deleteSession(id);
    setSessions(sessions.filter((s) => s._id !== id));
  };

  const handleStatusChange = async (id, action) => {
    switch (action) {
      case 'start':
        await api.startSession(id);
        break;
      case 'pause':
        await api.pauseSession(id);
        break;
      case 'resume':
        await api.resumeSession(id);
        break;
      case 'complete':
        await api.completeSession(id);
        break;
    }
    await fetchSessions();
  };

  const filteredSessions = sessions.filter((session) => {
    if (filter === 'all') return true;
    return session.status === filter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Sessions</h1>
          <p className="text-gray-400 mt-1">Create and manage classroom monitoring sessions</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          <Plus className="h-5 w-5 mr-2" />
          New Session
        </button>
      </div>

      {/* Filters */}
      <div className="flex space-x-2">
        {['all', 'created', 'running', 'paused', 'completed'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === status
                ? 'bg-primary-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
            }`}
          >
            {status.charAt(0).toUpperCase() + status.slice(1)}
          </button>
        ))}
      </div>

      {/* Sessions Grid */}
      {loading ? (
        <div className="bg-gray-800 rounded-xl p-12 text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500 mx-auto"></div>
          <p className="text-gray-400 mt-3">Loading sessions...</p>
        </div>
      ) : filteredSessions.length === 0 ? (
        <div className="bg-gray-800 rounded-xl p-12 text-center">
          <Video className="h-12 w-12 mx-auto text-gray-600 mb-4" />
          <p className="text-gray-400">
            {filter === 'all' ? 'No sessions yet' : `No ${filter} sessions`}
          </p>
          {filter === 'all' && (
            <button
              onClick={() => setShowModal(true)}
              className="mt-4 text-primary-400 hover:text-primary-300"
            >
              Create your first session
            </button>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSessions.map((session) => (
            <SessionCard
              key={session._id}
              session={session}
              onDelete={handleDeleteSession}
              onStatusChange={handleStatusChange}
            />
          ))}
        </div>
      )}

      {/* Create Session Modal */}
      <CreateSessionModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onCreate={handleCreateSession}
      />
    </div>
  );
}

export default Sessions;
