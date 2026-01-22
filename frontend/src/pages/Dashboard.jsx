import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import {
  Users,
  Video,
  Activity,
  AlertTriangle,
  TrendingUp,
  Clock,
  UserCheck,
  PlayCircle,
} from 'lucide-react';

function StatCard({ icon: Icon, label, value, subValue, color = 'primary' }) {
  const colorClasses = {
    primary: 'bg-primary-600/20 text-primary-400',
    green: 'bg-green-600/20 text-green-400',
    yellow: 'bg-yellow-600/20 text-yellow-400',
    red: 'bg-red-600/20 text-red-400',
    blue: 'bg-blue-600/20 text-blue-400',
  };

  return (
    <div className="bg-gray-800 rounded-xl p-6">
      <div className="flex items-center space-x-4">
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="h-6 w-6" />
        </div>
        <div>
          <p className="text-sm text-gray-400">{label}</p>
          <p className="text-2xl font-bold text-white">{value}</p>
          {subValue && <p className="text-xs text-gray-500 mt-1">{subValue}</p>}
        </div>
      </div>
    </div>
  );
}

function RecentSessionCard({ session }) {
  const statusColors = {
    created: 'bg-gray-500',
    running: 'bg-green-500',
    paused: 'bg-yellow-500',
    completed: 'bg-blue-500',
  };

  return (
    <div className="bg-gray-700/50 rounded-lg p-4 flex items-center justify-between">
      <div className="flex items-center space-x-3">
        <div className={`w-2 h-2 rounded-full ${statusColors[session.status]}`} />
        <div>
          <p className="text-white font-medium">{session.name}</p>
          <p className="text-sm text-gray-400">
            {new Date(session.createdAt).toLocaleDateString()} • {session.courseName}
          </p>
        </div>
      </div>
      <Link
        to={session.status === 'completed' ? `/sessions/${session._id}/analytics` : `/sessions/${session._id}/monitor`}
        className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
      >
        {session.status === 'completed' ? 'View Analytics' : 'Monitor'}
      </Link>
    </div>
  );
}

function Dashboard() {
  const [stats, setStats] = useState({
    totalStudents: 0,
    enrolledStudents: 0,
    totalSessions: 0,
    activeSessions: 0,
  });
  const [recentSessions, setRecentSessions] = useState([]);
  const [loading, setLoading] = useState(false); // Start with false for instant render

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    try {
      const [studentsRes, sessionsRes] = await Promise.all([
        api.getStudents({ limit: 100 }), // Reduced limit for speed
        api.getSessions({ limit: 5, sortBy: 'createdAt', sortOrder: 'desc' }), // Only fetch what we need
      ]);

      const students = studentsRes.data?.students || [];
      const sessions = sessionsRes.data?.sessions || [];

      setStats({
        totalStudents: studentsRes.data?.pagination?.total || students.length,
        enrolledStudents: students.filter((s) => s.enrollmentStatus === 'enrolled').length,
        totalSessions: sessionsRes.data?.pagination?.total || sessions.length,
        activeSessions: sessions.filter((s) => s.status === 'running').length,
      });

      setRecentSessions(sessions);
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1">Overview of your classroom analytics system</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={Users}
          label="Total Students"
          value={loading ? '...' : stats.totalStudents}
          subValue={loading ? '' : `${stats.enrolledStudents} enrolled`}
          color="primary"
        />
        <StatCard
          icon={UserCheck}
          label="Enrolled Students"
          value={loading ? '...' : stats.enrolledStudents}
          color="green"
        />
        <StatCard
          icon={Video}
          label="Total Sessions"
          value={loading ? '...' : stats.totalSessions}
          color="blue"
        />
        <StatCard
          icon={PlayCircle}
          label="Active Sessions"
          value={loading ? '...' : stats.activeSessions}
          color="yellow"
        />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Sessions */}
        <div className="bg-gray-800 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">Recent Sessions</h2>
            <Link
              to="/sessions"
              className="text-sm text-primary-400 hover:text-primary-300 transition-colors"
            >
              View All
            </Link>
          </div>

          {recentSessions.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              <Video className="h-12 w-12 mx-auto mb-3 opacity-50" />
              <p>No sessions yet</p>
              <Link
                to="/sessions"
                className="text-primary-400 hover:text-primary-300 text-sm mt-2 inline-block"
              >
                Create your first session
              </Link>
            </div>
          ) : (
            <div className="space-y-3">
              {recentSessions.map((session) => (
                <RecentSessionCard key={session._id} session={session} />
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-gray-800 rounded-xl p-6">
          <h2 className="text-lg font-semibold text-white mb-4">Quick Actions</h2>
          <div className="grid grid-cols-2 gap-4">
            <Link
              to="/sessions"
              className="flex flex-col items-center justify-center p-6 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors group"
            >
              <Video className="h-8 w-8 text-primary-400 group-hover:text-primary-300 mb-2" />
              <span className="text-white font-medium">New Session</span>
              <span className="text-xs text-gray-400 mt-1">Start monitoring</span>
            </Link>
            <Link
              to="/students"
              className="flex flex-col items-center justify-center p-6 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors group"
            >
              <Users className="h-8 w-8 text-green-400 group-hover:text-green-300 mb-2" />
              <span className="text-white font-medium">Add Student</span>
              <span className="text-xs text-gray-400 mt-1">Enroll new student</span>
            </Link>
            <Link
              to="/students"
              className="flex flex-col items-center justify-center p-6 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors group"
            >
              <UserCheck className="h-8 w-8 text-blue-400 group-hover:text-blue-300 mb-2" />
              <span className="text-white font-medium">Manage Students</span>
              <span className="text-xs text-gray-400 mt-1">View all students</span>
            </Link>
            <Link
              to="/sessions"
              className="flex flex-col items-center justify-center p-6 bg-gray-700/50 rounded-lg hover:bg-gray-700 transition-colors group"
            >
              <Activity className="h-8 w-8 text-yellow-400 group-hover:text-yellow-300 mb-2" />
              <span className="text-white font-medium">View Analytics</span>
              <span className="text-xs text-gray-400 mt-1">Session reports</span>
            </Link>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4">System Information</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="flex items-center space-x-3 p-4 bg-gray-700/50 rounded-lg">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <div>
              <p className="text-white font-medium">AI Service</p>
              <p className="text-xs text-gray-400">Running - YOLOv8, InsightFace, MediaPipe</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 p-4 bg-gray-700/50 rounded-lg">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <div>
              <p className="text-white font-medium">Database</p>
              <p className="text-xs text-gray-400">MongoDB Connected</p>
            </div>
          </div>
          <div className="flex items-center space-x-3 p-4 bg-gray-700/50 rounded-lg">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <div>
              <p className="text-white font-medium">WebSocket</p>
              <p className="text-xs text-gray-400">Real-time updates enabled</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
