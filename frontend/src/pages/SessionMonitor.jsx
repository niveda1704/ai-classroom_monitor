import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useSession } from '../contexts/SessionContext';
import {
  Play,
  Pause,
  StopCircle,
  Users,
  Eye,
  EyeOff,
  Smartphone,
  AlertTriangle,
  Activity,
  Clock,
  Camera,
  Maximize,
  RefreshCw,
} from 'lucide-react';

function MetricCard({ icon: Icon, label, value, color = 'primary', trend }) {
  const colorClasses = {
    primary: 'text-primary-400',
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
    blue: 'text-blue-400',
  };

  return (
    <div className="bg-gray-700/50 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <Icon className={`h-5 w-5 ${colorClasses[color]}`} />
        {trend !== undefined && (
          <span className={trend >= 0 ? 'text-green-400 text-xs' : 'text-red-400 text-xs'}>
            {trend >= 0 ? '+' : ''}{trend}%
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="text-sm text-gray-400">{label}</p>
    </div>
  );
}

function EventItem({ event }) {
  const eventConfig = {
    attention_drop: { icon: EyeOff, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
    phone_detected: { icon: Smartphone, color: 'text-red-400', bg: 'bg-red-500/20' },
    poor_posture: { icon: AlertTriangle, color: 'text-orange-400', bg: 'bg-orange-500/20' },
    student_identified: { icon: Users, color: 'text-green-400', bg: 'bg-green-500/20' },
    looking_away: { icon: EyeOff, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
    distraction: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/20' },
  };

  const config = eventConfig[event.eventType] || {
    icon: Activity,
    color: 'text-gray-400',
    bg: 'bg-gray-500/20',
  };

  const Icon = config.icon;

  return (
    <div className={`flex items-start space-x-3 p-3 rounded-lg ${config.bg}`}>
      <Icon className={`h-5 w-5 mt-0.5 ${config.color}`} />
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-medium">
          {event.studentName || event.trackId || 'Unknown'} - {event.eventType.replace(/_/g, ' ')}
        </p>
        {event.details && (
          <p className="text-gray-400 text-xs mt-0.5 truncate">{JSON.stringify(event.details)}</p>
        )}
        <p className="text-gray-500 text-xs mt-1">
          {new Date(event.timestamp).toLocaleTimeString()}
        </p>
      </div>
    </div>
  );
}

function StudentCard({ student }) {
  const attentionColor = student.attention >= 70 
    ? 'text-green-400' 
    : student.attention >= 40 
    ? 'text-yellow-400' 
    : 'text-red-400';

  return (
    <div className="bg-gray-700/50 rounded-lg p-3 flex items-center space-x-3">
      <div className="w-10 h-10 rounded-full bg-gray-600 flex items-center justify-center text-white font-semibold">
        {student.name?.charAt(0)?.toUpperCase() || '?'}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-white text-sm font-medium truncate">
          {student.name || `Track ${student.trackId}`}
        </p>
        <p className={`text-xs ${attentionColor}`}>
          {student.attention?.toFixed(0) || 0}% attention
        </p>
      </div>
      <div className="flex items-center space-x-1">
        {student.lookingAway && <EyeOff className="h-4 w-4 text-yellow-400" />}
        {student.phoneDetected && <Smartphone className="h-4 w-4 text-red-400" />}
        {student.poorPosture && <AlertTriangle className="h-4 w-4 text-orange-400" />}
      </div>
    </div>
  );
}

function SessionMonitor() {
  const { id } = useParams();
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);
  const frameIntervalRef = useRef(null);

  const { metrics, events, students, startMonitoring, stopMonitoring, isConnected } = useSession();

  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [cameraActive, setCameraActive] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [fps, setFps] = useState(2); // Reduced from 5 to 2 FPS to prevent too many requests
  const [error, setError] = useState('');
  const [elapsedTime, setElapsedTime] = useState(0);
  const [isEnding, setIsEnding] = useState(false); // Flag to stop all processing

  useEffect(() => {
    fetchSession();
    return () => {
      stopCamera();
      stopMonitoring();
    };
  }, [id]);

  // Elapsed time counter
  useEffect(() => {
    let interval;
    if (session?.status === 'running') {
      interval = setInterval(() => {
        setElapsedTime((prev) => prev + 1);
      }, 1000);
    }
    return () => clearInterval(interval);
  }, [session?.status]);

  const fetchSession = async () => {
    try {
      const response = await api.getSession(id);
      setSession(response.data?.session);
      
      if (response.data?.session?.status === 'running') {
        await startMonitoring(response.data.session);
      }
    } catch (err) {
      setError('Failed to load session');
    } finally {
      setLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      setError('');
      console.log('Requesting camera access...');
      
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 1280 }, 
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });
      
      console.log('Camera stream obtained:', stream);
      streamRef.current = stream;
      
      // Set camera active first so video element becomes visible
      setCameraActive(true);
      
      // Use setTimeout to ensure React has rendered the video element
      setTimeout(() => {
        if (videoRef.current) {
          console.log('Attaching stream to video element...');
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            console.log('Video metadata loaded, playing...');
            videoRef.current.play().catch(e => console.error('Play error:', e));
          };
        } else {
          console.error('Video ref not available');
        }
      }, 100);
    } catch (err) {
      console.error('Camera error:', err);
      if (err.name === 'NotAllowedError') {
        setError('Camera access denied. Please allow camera permissions and reload.');
      } else if (err.name === 'NotFoundError') {
        setError('No camera found. Please connect a camera and reload.');
      } else {
        setError(`Camera error: ${err.message}`);
      }
    }
  };

  const stopCamera = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const handleStartSession = async () => {
    try {
      await api.startSession(id);
      await startCamera();
      await startMonitoring({ ...session, status: 'running' });
      setSession({ ...session, status: 'running' });
      setElapsedTime(0);
      
      // Start frame processing
      startFrameProcessing();
    } catch (err) {
      setError(err.message || 'Failed to start session');
    }
  };

  const handlePauseSession = async () => {
    try {
      await api.pauseSession(id);
      stopFrameProcessing();
      setSession({ ...session, status: 'paused' });
    } catch (err) {
      setError(err.message || 'Failed to pause session');
    }
  };

  const handleResumeSession = async () => {
    try {
      await api.resumeSession(id);
      setSession({ ...session, status: 'running' });
      startFrameProcessing();
    } catch (err) {
      setError(err.message || 'Failed to resume session');
    }
  };

  const handleStopSession = async () => {
    if (!window.confirm('Are you sure you want to end this session?')) return;
    
    // Set flag to stop all processing immediately
    setIsEnding(true);
    
    // Stop frame processing first
    stopFrameProcessing();
    stopCamera();
    stopMonitoring();
    
    try {
      // Then complete the session
      await api.completeSession(id);
    } catch (err) {
      console.error('Stop session error:', err);
    }
    
    // Navigate to analytics
    navigate(`/sessions/${id}/analytics`);
  };

  // Local state for real-time metrics (independent of WebSocket)
  const [localMetrics, setLocalMetrics] = useState({
    studentCount: 0,
    avgAttention: 0,
    phoneUsage: 0,
    distractions: 0
  });
  const [localStudents, setLocalStudents] = useState([]);
  const [localEvents, setLocalEvents] = useState([]);

  const startFrameProcessing = useCallback(() => {
    if (frameIntervalRef.current) return;

    frameIntervalRef.current = setInterval(async () => {
      // Skip if ending session, no video, no canvas, or already processing
      if (isEnding || !videoRef.current || !canvasRef.current || processing) return;

      setProcessing(true);
      try {
        const video = videoRef.current;
        const canvas = canvasRef.current;
        const ctx = canvas.getContext('2d');

        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        ctx.drawImage(video, 0, 0);

        const imageData = canvas.toDataURL('image/jpeg', 0.7);

        // Send frame to backend for AI processing
        const response = await api.processFrame(id, imageData);
        
        if (response.data && !isEnding) {
          // Update local metrics directly from response
          const data = response.data;
          
          if (data.metrics) {
            setLocalMetrics({
              studentCount: data.metrics.studentCount || 0,
              avgAttention: Math.round(data.metrics.avgAttention || 0),
              phoneUsage: data.metrics.phoneUsage || 0,
              distractions: data.metrics.distractions || 0
            });
          }
          
          if (data.students && data.students.length > 0) {
            setLocalStudents(data.students);
          }
          
          if (data.events && data.events.length > 0) {
            setLocalEvents(prev => {
              const newEvents = [...data.events, ...prev].slice(0, 50);
              return newEvents;
            });
          }
        }
      } catch (err) {
        console.error('Frame processing error:', err);
      } finally {
        setProcessing(false);
      }
    }, 1000 / fps);
  }, [fps, processing, id, isEnding]);

  const stopFrameProcessing = () => {
    if (frameIntervalRef.current) {
      clearInterval(frameIntervalRef.current);
      frameIntervalRef.current = null;
    }
  };

  const formatTime = (seconds) => {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 mx-auto text-red-400 mb-4" />
        <p className="text-gray-400">Session not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white">{session.name}</h1>
          <p className="text-gray-400 mt-1">{session.courseName}</p>
        </div>
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2 bg-gray-800 px-4 py-2 rounded-lg">
            <Clock className="h-5 w-5 text-primary-400" />
            <span className="text-white font-mono">{formatTime(elapsedTime)}</span>
          </div>
          <div className={`flex items-center space-x-2 px-3 py-1.5 rounded-full ${
            isConnected ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm">{isConnected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-xl text-red-400">
          {error}
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Video Feed */}
        <div className="lg:col-span-2">
          <div className="bg-gray-800 rounded-xl overflow-hidden">
            <div className="relative aspect-video bg-gray-900">
              {/* Video element - always render but hide when not active */}
              <video
                ref={videoRef}
                className={`absolute inset-0 w-full h-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
                autoPlay
                playsInline
                muted
                style={{ transform: 'scaleX(-1)' }}
              />
              {!cameraActive && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="text-center">
                    <Camera className="h-16 w-16 mx-auto text-gray-600 mb-4" />
                    <p className="text-gray-400">Camera not active</p>
                    <p className="text-gray-500 text-sm mt-1">Start the session to begin monitoring</p>
                  </div>
                </div>
              )}

              {/* Processing indicator */}
              {processing && (
                <div className="absolute top-4 right-4 flex items-center space-x-2 bg-black/50 px-3 py-1.5 rounded-full">
                  <RefreshCw className="h-4 w-4 text-primary-400 animate-spin" />
                  <span className="text-white text-sm">Processing</span>
                </div>
              )}

              {/* FPS indicator */}
              {cameraActive && (
                <div className="absolute bottom-4 left-4 bg-black/50 px-3 py-1.5 rounded-full">
                  <span className="text-white text-sm">{fps} FPS</span>
                </div>
              )}
            </div>

            <canvas ref={canvasRef} className="hidden" />

            {/* Controls */}
            <div className="p-4 border-t border-gray-700">
              <div className="flex items-center justify-center space-x-4">
                {session.status === 'created' && (
                  <button
                    onClick={handleStartSession}
                    className="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors flex items-center"
                  >
                    <Play className="h-5 w-5 mr-2" />
                    Start Session
                  </button>
                )}

                {session.status === 'running' && (
                  <>
                    <button
                      onClick={handlePauseSession}
                      className="px-6 py-2.5 bg-yellow-600 hover:bg-yellow-700 text-white font-medium rounded-lg transition-colors flex items-center"
                    >
                      <Pause className="h-5 w-5 mr-2" />
                      Pause
                    </button>
                    <button
                      onClick={handleStopSession}
                      className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors flex items-center"
                    >
                      <StopCircle className="h-5 w-5 mr-2" />
                      End Session
                    </button>
                  </>
                )}

                {session.status === 'paused' && (
                  <>
                    <button
                      onClick={handleResumeSession}
                      className="px-6 py-2.5 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition-colors flex items-center"
                    >
                      <Play className="h-5 w-5 mr-2" />
                      Resume
                    </button>
                    <button
                      onClick={handleStopSession}
                      className="px-6 py-2.5 bg-red-600 hover:bg-red-700 text-white font-medium rounded-lg transition-colors flex items-center"
                    >
                      <StopCircle className="h-5 w-5 mr-2" />
                      End Session
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Live Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-4">
            <MetricCard
              icon={Users}
              label="Students"
              value={localMetrics.studentCount || metrics?.totalDetected || students.length || 0}
              color="primary"
            />
            <MetricCard
              icon={Eye}
              label="Avg Attention"
              value={`${localMetrics.avgAttention || metrics?.avgAttention?.toFixed(0) || 0}%`}
              color={(localMetrics.avgAttention || metrics?.avgAttention || 0) >= 70 ? 'green' : (localMetrics.avgAttention || metrics?.avgAttention || 0) >= 40 ? 'yellow' : 'red'}
            />
            <MetricCard
              icon={Smartphone}
              label="Phone Usage"
              value={localMetrics.phoneUsage || metrics?.phoneCount || 0}
              color="red"
            />
            <MetricCard
              icon={AlertTriangle}
              label="Distractions"
              value={localMetrics.distractions || metrics?.distractionCount || 0}
              color="yellow"
            />
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Students List */}
          <div className="bg-gray-800 rounded-xl p-4">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
              <Users className="h-5 w-5 mr-2 text-primary-400" />
              Detected Students ({localStudents.length || students.length})
            </h2>
            {(localStudents.length || students.length) === 0 ? (
              <p className="text-gray-400 text-sm text-center py-4">No students detected yet</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {(localStudents.length > 0 ? localStudents : students).map((student, index) => (
                  <StudentCard key={student.studentId || student.trackId || index} student={student} />
                ))}
              </div>
            )}
          </div>

          {/* Event Log */}
          <div className="bg-gray-800 rounded-xl p-4">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
              <Activity className="h-5 w-5 mr-2 text-primary-400" />
              Event Log ({localEvents.length || events.length})
            </h2>
            {(localEvents.length || events.length) === 0 ? (
              <p className="text-gray-400 text-sm text-center py-4">No events recorded yet</p>
            ) : (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {(localEvents.length > 0 ? localEvents : events).slice(0, 20).map((event, index) => (
                  <EventItem key={event._id || index} event={event} />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default SessionMonitor;
