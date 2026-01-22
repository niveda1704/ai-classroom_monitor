import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import {
  Camera,
  CheckCircle,
  AlertCircle,
  RotateCcw,
  ArrowLeft,
  User,
  Loader,
} from 'lucide-react';

function StudentEnrollment() {
  const { id } = useParams();
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const streamRef = useRef(null);

  const [student, setStudent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [enrollmentState, setEnrollmentState] = useState('idle'); // idle, enrolling, capturing, processing, completed, error
  const [capturedImages, setCapturedImages] = useState(0);
  const [requiredImages, setRequiredImages] = useState(15);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [cameraActive, setCameraActive] = useState(false);

  useEffect(() => {
    fetchStudent();
    return () => {
      stopCamera();
    };
  }, [id]);

  const fetchStudent = async () => {
    try {
      const response = await api.getStudent(id);
      setStudent(response.data?.student);
      
      if (response.data?.student?.enrollmentStatus === 'enrolled') {
        setEnrollmentState('completed');
      } else if (response.data?.student?.enrollmentStatus === 'in_progress') {
        setEnrollmentState('enrolling');
        setCapturedImages(response.data?.student?.tempEmbeddingsCount || 0);
      }
    } catch (err) {
      setError('Failed to load student');
    } finally {
      setLoading(false);
    }
  };

  const startCamera = async () => {
    try {
      console.log('Requesting camera access for enrollment...');
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { 
          width: { ideal: 640 }, 
          height: { ideal: 480 }, 
          facingMode: 'user' 
        },
      });
      console.log('Camera stream obtained:', stream);
      streamRef.current = stream;
      
      // Set camera active first so video element becomes visible
      setCameraActive(true);
      setError('');
      
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
        setError('Camera access denied. Please allow camera permissions in your browser and reload.');
      } else if (err.name === 'NotFoundError') {
        setError('No camera found. Please connect a camera and reload.');
      } else {
        setError(`Camera error: ${err.message}`);
      }
    }
  };

  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    setCameraActive(false);
  };

  const startEnrollment = async () => {
    try {
      setError('');
      setMessage('Starting enrollment...');
      
      await api.startEnrollment(id, requiredImages);
      setEnrollmentState('enrolling');
      setCapturedImages(0);
      await startCamera();
      setMessage('Look at the camera and click capture to take photos from different angles.');
    } catch (err) {
      setError(err.message || 'Failed to start enrollment');
    }
  };

  const captureImage = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || enrollmentState !== 'enrolling') return;

    try {
      setEnrollmentState('capturing');
      const video = videoRef.current;
      const canvas = canvasRef.current;
      const ctx = canvas.getContext('2d');

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0);

      const imageData = canvas.toDataURL('image/jpeg', 0.8);

      const response = await api.captureEnrollment(id, imageData);
      const data = response.data;

      if (data.faceDetected) {
        setCapturedImages(data.capturedCount);
        setMessage(`Captured ${data.capturedCount}/${data.requiredCount} images. ${data.requiredCount - data.capturedCount} more needed.`);
        
        if (data.capturedCount >= data.requiredCount) {
          setEnrollmentState('processing');
          setMessage('Processing face embeddings...');
          
          try {
            await api.completeEnrollment(id);
            setEnrollmentState('completed');
            setMessage('Enrollment completed successfully!');
            stopCamera();
          } catch (completeErr) {
            setError(completeErr.message || 'Failed to complete enrollment');
            setEnrollmentState('enrolling');
          }
        } else {
          setEnrollmentState('enrolling');
        }
      } else {
        setError('No face detected. Please ensure your face is visible and well-lit.');
        setEnrollmentState('enrolling');
      }
    } catch (err) {
      setError(err.message || 'Failed to capture image');
      setEnrollmentState('enrolling');
    }
  }, [id, enrollmentState]);

  const resetEnrollment = async () => {
    try {
      setError('');
      await api.resetEnrollment(id);
      setEnrollmentState('idle');
      setCapturedImages(0);
      setMessage('');
      stopCamera();
    } catch (err) {
      setError(err.message || 'Failed to reset enrollment');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    );
  }

  if (!student) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto text-red-400 mb-4" />
        <p className="text-gray-400">Student not found</p>
        <button
          onClick={() => navigate('/students')}
          className="mt-4 text-primary-400 hover:text-primary-300"
        >
          Back to Students
        </button>
      </div>
    );
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center space-x-4">
        <button
          onClick={() => navigate('/students')}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-white">Student Enrollment</h1>
          <p className="text-gray-400 mt-1">Capture face images for recognition</p>
        </div>
      </div>

      {/* Student Info */}
      <div className="bg-gray-800 rounded-xl p-6">
        <div className="flex items-center space-x-4">
          <div className="w-16 h-16 rounded-full bg-gray-700 flex items-center justify-center">
            <User className="h-8 w-8 text-gray-400" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-white">{student.name}</h2>
            <p className="text-gray-400">ID: {student.studentId}</p>
            {student.course && <p className="text-gray-400 text-sm">{student.course}</p>}
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 bg-red-500/20 border border-red-500/50 rounded-xl flex items-center space-x-3 text-red-400">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Success Message */}
      {message && !error && (
        <div className={`p-4 rounded-xl flex items-center space-x-3 ${
          enrollmentState === 'completed' 
            ? 'bg-green-500/20 border border-green-500/50 text-green-400'
            : 'bg-blue-500/20 border border-blue-500/50 text-blue-400'
        }`}>
          {enrollmentState === 'completed' ? (
            <CheckCircle className="h-5 w-5 flex-shrink-0" />
          ) : (
            <Camera className="h-5 w-5 flex-shrink-0" />
          )}
          <p>{message}</p>
        </div>
      )}

      {/* Camera View */}
      <div className="bg-gray-800 rounded-xl overflow-hidden">
        <div className="relative aspect-video bg-gray-900">
          {/* Video element - always render it but hide when not active */}
          <video
            ref={videoRef}
            className={`absolute inset-0 w-full h-full object-cover ${cameraActive ? 'block' : 'hidden'}`}
            style={{ transform: 'scaleX(-1)' }}
            autoPlay
            playsInline
            muted
          />
          {!cameraActive ? (
            <div className="absolute inset-0 flex items-center justify-center">
              {enrollmentState === 'completed' ? (
                <div className="text-center">
                  <CheckCircle className="h-16 w-16 mx-auto text-green-500 mb-4" />
                  <p className="text-white font-medium">Enrollment Complete</p>
                  <p className="text-gray-400 text-sm mt-1">This student is ready for recognition</p>
                </div>
              ) : (
                <div className="text-center">
                  <Camera className="h-16 w-16 mx-auto text-gray-600 mb-4" />
                  <p className="text-gray-400">Camera preview will appear here</p>
                </div>
              )}
            </div>
          ) : null}

          {/* Face guide overlay */}
          {cameraActive && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-48 h-64 border-2 border-dashed border-primary-400/50 rounded-full"></div>
            </div>
          )}
        </div>

        {/* Hidden canvas for capture */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Progress Bar */}
        {(enrollmentState === 'enrolling' || enrollmentState === 'capturing') && (
          <div className="px-6 py-4 border-t border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm text-gray-400">Progress</span>
              <span className="text-sm text-white font-medium">
                {capturedImages} / {requiredImages} images
              </span>
            </div>
            <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-primary-500 transition-all duration-300"
                style={{ width: `${(capturedImages / requiredImages) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="p-6 border-t border-gray-700">
          {enrollmentState === 'idle' && (
            <button
              onClick={startEnrollment}
              className="w-full py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
            >
              <Camera className="h-5 w-5 mr-2" />
              Start Enrollment
            </button>
          )}

          {(enrollmentState === 'enrolling' || enrollmentState === 'capturing') && (
            <div className="flex space-x-4">
              <button
                onClick={captureImage}
                disabled={enrollmentState === 'capturing'}
                className="flex-1 py-3 px-4 bg-primary-600 hover:bg-primary-700 disabled:bg-primary-600/50 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
              >
                {enrollmentState === 'capturing' ? (
                  <Loader className="h-5 w-5 animate-spin mr-2" />
                ) : (
                  <Camera className="h-5 w-5 mr-2" />
                )}
                {enrollmentState === 'capturing' ? 'Capturing...' : 'Capture Photo'}
              </button>
              <button
                onClick={resetEnrollment}
                className="py-3 px-4 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
              >
                <RotateCcw className="h-5 w-5" />
              </button>
            </div>
          )}

          {enrollmentState === 'processing' && (
            <div className="flex items-center justify-center py-3 text-primary-400">
              <Loader className="h-5 w-5 animate-spin mr-2" />
              Processing embeddings...
            </div>
          )}

          {enrollmentState === 'completed' && (
            <div className="flex space-x-4">
              <button
                onClick={() => navigate('/students')}
                className="flex-1 py-3 px-4 bg-primary-600 hover:bg-primary-700 text-white font-medium rounded-lg transition-colors"
              >
                Back to Students
              </button>
              <button
                onClick={resetEnrollment}
                className="py-3 px-4 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors flex items-center justify-center"
                title="Re-enroll"
              >
                <RotateCcw className="h-5 w-5" />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Instructions */}
      <div className="bg-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Enrollment Instructions</h3>
        <ul className="space-y-2 text-gray-400 text-sm">
          <li className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Position your face within the oval guide</span>
          </li>
          <li className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Ensure good lighting on your face</span>
          </li>
          <li className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Capture photos from different angles (front, left, right, up, down)</span>
          </li>
          <li className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Remove glasses or accessories that may obstruct face detection</span>
          </li>
          <li className="flex items-start space-x-2">
            <CheckCircle className="h-4 w-4 text-green-500 mt-0.5 flex-shrink-0" />
            <span>Maintain neutral expression during capture</span>
          </li>
        </ul>
      </div>
    </div>
  );
}

export default StudentEnrollment;
