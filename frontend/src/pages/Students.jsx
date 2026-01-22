import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import api from '../services/api';
import {
  Plus,
  Search,
  UserPlus,
  Edit2,
  Trash2,
  Camera,
  CheckCircle,
  AlertCircle,
  X,
} from 'lucide-react';

function AddStudentModal({ isOpen, onClose, onAdd }) {
  const [formData, setFormData] = useState({
    name: '',
    studentId: '',
    email: '',
    course: '',
    department: '',
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
      await onAdd(formData);
      setFormData({ name: '', studentId: '', email: '', course: '', department: '' });
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
          <h2 className="text-lg font-semibold text-white">Add New Student</h2>
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
              Full Name *
            </label>
            <input
              type="text"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter student name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Student ID *
            </label>
            <input
              type="text"
              name="studentId"
              value={formData.studentId}
              onChange={handleChange}
              required
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter student ID"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Email
            </label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter email address"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Course
            </label>
            <input
              type="text"
              name="course"
              value={formData.course}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter course name"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Department
            </label>
            <input
              type="text"
              name="department"
              value={formData.department}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
              placeholder="Enter department"
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
                'Add Student'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function StudentRow({ student, onDelete }) {
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    if (!window.confirm('Are you sure you want to delete this student?')) return;
    setDeleting(true);
    try {
      await onDelete(student._id);
    } catch (error) {
      console.error('Delete failed:', error);
    } finally {
      setDeleting(false);
    }
  };

  const statusColors = {
    not_enrolled: { bg: 'bg-gray-500/20', text: 'text-gray-400', label: 'Not Enrolled' },
    in_progress: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: 'In Progress' },
    enrolled: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Enrolled' },
  };

  const status = statusColors[student.enrollmentStatus] || statusColors.not_enrolled;

  return (
    <tr className="border-b border-gray-700 hover:bg-gray-700/50 transition-colors">
      <td className="py-4 px-4">
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center text-white font-semibold">
            {student.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="text-white font-medium">{student.name}</p>
            <p className="text-sm text-gray-400">{student.studentId}</p>
          </div>
        </div>
      </td>
      <td className="py-4 px-4 text-gray-300">{student.email || '-'}</td>
      <td className="py-4 px-4 text-gray-300">{student.course || '-'}</td>
      <td className="py-4 px-4">
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium ${status.bg} ${status.text}`}>
          {student.enrollmentStatus === 'enrolled' && <CheckCircle className="h-3 w-3 mr-1" />}
          {status.label}
        </span>
      </td>
      <td className="py-4 px-4">
        <div className="flex items-center space-x-2">
          {student.enrollmentStatus !== 'enrolled' && (
            <Link
              to={`/students/${student._id}/enroll`}
              className="p-2 text-primary-400 hover:text-primary-300 hover:bg-gray-600 rounded-lg transition-colors"
              title="Enroll Student"
            >
              <Camera className="h-4 w-4" />
            </Link>
          )}
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="p-2 text-red-400 hover:text-red-300 hover:bg-gray-600 rounded-lg transition-colors disabled:opacity-50"
            title="Delete Student"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

function Students() {
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchStudents();
  }, []);

  const fetchStudents = async () => {
    setLoading(true);
    try {
      const response = await api.getStudents({ limit: 100 });
      setStudents(response.data?.students || []);
    } catch (error) {
      console.error('Failed to fetch students:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAddStudent = async (data) => {
    await api.createStudent(data);
    await fetchStudents();
  };

  const handleDeleteStudent = async (id) => {
    await api.deleteStudent(id);
    setStudents(students.filter((s) => s._id !== id));
  };

  const filteredStudents = students.filter((student) => {
    const matchesSearch =
      student.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      student.studentId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (student.email && student.email.toLowerCase().includes(searchQuery.toLowerCase()));

    const matchesFilter =
      filter === 'all' ||
      (filter === 'enrolled' && student.enrollmentStatus === 'enrolled') ||
      (filter === 'not_enrolled' && student.enrollmentStatus !== 'enrolled');

    return matchesSearch && matchesFilter;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">Students</h1>
          <p className="text-gray-400 mt-1">Manage and enroll students for face recognition</p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="inline-flex items-center px-4 py-2.5 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
        >
          <Plus className="h-5 w-5 mr-2" />
          Add Student
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search students..."
            className="w-full pl-10 pr-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="px-4 py-2.5 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
        >
          <option value="all">All Students</option>
          <option value="enrolled">Enrolled Only</option>
          <option value="not_enrolled">Not Enrolled</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-gray-800 rounded-xl overflow-hidden">
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500 mx-auto"></div>
            <p className="text-gray-400 mt-3">Loading students...</p>
          </div>
        ) : filteredStudents.length === 0 ? (
          <div className="text-center py-12">
            <UserPlus className="h-12 w-12 mx-auto text-gray-600 mb-4" />
            <p className="text-gray-400">
              {searchQuery || filter !== 'all' ? 'No students found' : 'No students yet'}
            </p>
            {!searchQuery && filter === 'all' && (
              <button
                onClick={() => setShowModal(true)}
                className="mt-4 text-primary-400 hover:text-primary-300"
              >
                Add your first student
              </button>
            )}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-700/50">
                <tr>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">Student</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">Email</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">Course</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">Status</th>
                  <th className="text-left py-3 px-4 text-sm font-medium text-gray-300">Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredStudents.map((student) => (
                  <StudentRow
                    key={student._id}
                    student={student}
                    onDelete={handleDeleteStudent}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Add Student Modal */}
      <AddStudentModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        onAdd={handleAddStudent}
      />
    </div>
  );
}

export default Students;
