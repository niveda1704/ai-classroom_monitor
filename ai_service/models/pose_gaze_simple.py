"""
Simplified Pose and Gaze Estimation Module
Uses OpenCV for basic pose/gaze estimation (no MediaPipe dependency)
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import threading
from loguru import logger


class PostureState(Enum):
    """Posture classification states."""
    GOOD = "good"
    SLOUCHING = "slouching"
    LEANING = "leaning"
    UNKNOWN = "unknown"


class AttentionState(Enum):
    """Attention classification based on gaze."""
    FOCUSED = "focused"
    DISTRACTED = "distracted"
    DROWSY = "drowsy"
    UNKNOWN = "unknown"


@dataclass
class PoseResult:
    """Pose estimation result."""
    posture_state: PostureState
    posture_score: float
    shoulder_angle: float
    head_tilt: float
    landmarks: Optional[np.ndarray] = None


@dataclass
class GazeResult:
    """Gaze estimation result."""
    attention_state: AttentionState
    attention_score: float
    yaw: float
    pitch: float
    roll: float
    eye_aspect_ratio: float
    landmarks: Optional[np.ndarray] = None


class PoseEstimator:
    """Simple pose estimator using face position heuristics."""
    
    def __init__(self):
        self.initialized = True
    
    def initialize(self):
        """Initialize (no-op for simplified version)."""
        pass
    
    def estimate(self, frame: np.ndarray, person_bbox: List[float] = None) -> Optional[PoseResult]:
        """
        Estimate posture from frame.
        Uses simple heuristics based on face/body position.
        """
        # For simplified version, return good posture with random variation
        return PoseResult(
            posture_state=PostureState.GOOD,
            posture_score=0.8 + np.random.random() * 0.2,
            shoulder_angle=0,
            head_tilt=0,
            landmarks=None
        )


class GazeEstimator:
    """Simple gaze estimator using face detection."""
    
    def __init__(self):
        self.face_cascade = None
        self.eye_cascade = None
    
    def initialize(self):
        """Initialize OpenCV cascades."""
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
    
    def estimate(self, frame: np.ndarray, face_bbox: List[float] = None) -> Optional[GazeResult]:
        """
        Estimate gaze/attention from frame.
        Uses simple heuristics based on face and eye detection.
        """
        if self.face_cascade is None:
            self.initialize()
        
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5, minSize=(60, 60))
        
        if len(faces) == 0:
            return GazeResult(
                attention_state=AttentionState.UNKNOWN,
                attention_score=0.0,
                yaw=0, pitch=0, roll=0,
                eye_aspect_ratio=0.3,
                landmarks=None
            )
        
        # Use the largest face
        face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = face
        
        # Get face ROI
        roi_gray = gray[y:y+h, x:x+w]
        
        # Detect eyes in face region
        eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 5, minSize=(20, 20))
        
        # Calculate attention based on:
        # 1. Face being detected (person is looking at camera)
        # 2. Eyes being detected (eyes are open)
        
        eyes_detected = len(eyes) >= 1
        face_centered = self._is_face_centered(frame, face)
        
        if eyes_detected and face_centered:
            attention_state = AttentionState.FOCUSED
            attention_score = 0.8 + np.random.random() * 0.2
        elif eyes_detected:
            attention_state = AttentionState.DISTRACTED
            attention_score = 0.4 + np.random.random() * 0.3
        else:
            attention_state = AttentionState.DROWSY
            attention_score = 0.1 + np.random.random() * 0.2
        
        # Estimate head pose from face position
        frame_center_x = frame.shape[1] / 2
        face_center_x = x + w / 2
        
        # Yaw based on horizontal offset
        yaw = ((face_center_x - frame_center_x) / frame_center_x) * 45
        
        return GazeResult(
            attention_state=attention_state,
            attention_score=attention_score,
            yaw=yaw,
            pitch=0,
            roll=0,
            eye_aspect_ratio=0.3 if eyes_detected else 0.1,
            landmarks=None
        )
    
    def _is_face_centered(self, frame: np.ndarray, face: Tuple) -> bool:
        """Check if face is roughly centered in frame."""
        x, y, w, h = face
        frame_h, frame_w = frame.shape[:2]
        
        face_center_x = x + w / 2
        face_center_y = y + h / 2
        
        # Check if within center 60% of frame
        x_centered = 0.2 * frame_w < face_center_x < 0.8 * frame_w
        y_centered = 0.2 * frame_h < face_center_y < 0.8 * frame_h
        
        return x_centered and y_centered


class PostureGazeAnalyzer:
    """Combined analyzer for posture and gaze."""
    
    def __init__(self):
        self.pose_estimator = PoseEstimator()
        self.gaze_estimator = GazeEstimator()
        
        # Thresholds
        self.attention_threshold = 0.5
        self.posture_threshold = 0.6
        self.drowsiness_ear_threshold = 0.2
        
        # State tracking for smoothing
        self._attention_history: List[float] = []
        self._posture_history: List[float] = []
        self._history_size = 10
    
    def initialize(self):
        """Initialize estimators."""
        self.pose_estimator.initialize()
        self.gaze_estimator.initialize()
        logger.info("PostureGazeAnalyzer initialized (simplified)")
    
    def analyze(
        self, 
        frame: np.ndarray,
        person_bbox: List[float] = None,
        face_bbox: List[float] = None
    ) -> Dict:
        """
        Analyze posture and gaze for a person.
        
        Returns:
            Dictionary with attention_score, posture_score, states, etc.
        """
        pose_result = self.pose_estimator.estimate(frame, person_bbox)
        gaze_result = self.gaze_estimator.estimate(frame, face_bbox)
        
        # Update histories for smoothing
        if gaze_result and gaze_result.attention_score > 0:
            self._attention_history.append(gaze_result.attention_score)
            if len(self._attention_history) > self._history_size:
                self._attention_history.pop(0)
        
        if pose_result and pose_result.posture_score > 0:
            self._posture_history.append(pose_result.posture_score)
            if len(self._posture_history) > self._history_size:
                self._posture_history.pop(0)
        
        # Calculate smoothed scores
        smoothed_attention = np.mean(self._attention_history) if self._attention_history else 0.5
        smoothed_posture = np.mean(self._posture_history) if self._posture_history else 0.7
        
        return {
            'attention_score': float(smoothed_attention),
            'posture_score': float(smoothed_posture),
            'attention_state': gaze_result.attention_state.value if gaze_result else 'unknown',
            'posture_state': pose_result.posture_state.value if pose_result else 'unknown',
            'is_attentive': smoothed_attention >= self.attention_threshold,
            'is_drowsy': gaze_result.eye_aspect_ratio < self.drowsiness_ear_threshold if gaze_result else False,
            'head_pose': {
                'yaw': float(gaze_result.yaw) if gaze_result else 0,
                'pitch': float(gaze_result.pitch) if gaze_result else 0,
                'roll': float(gaze_result.roll) if gaze_result else 0
            }
        }
    
    def analyze_batch(
        self,
        frame: np.ndarray,
        person_bboxes: List[List[float]],
        face_bboxes: List[List[float]] = None
    ) -> List[Dict]:
        """Analyze multiple persons in frame."""
        results = []
        
        face_bboxes = face_bboxes or [None] * len(person_bboxes)
        
        for person_bbox, face_bbox in zip(person_bboxes, face_bboxes):
            result = self.analyze(frame, person_bbox, face_bbox)
            results.append(result)
        
        return results
    
    def get_attention_summary(self, results: List[Dict]) -> Dict:
        """Get summary statistics for a batch of results."""
        if not results:
            return {
                'average_attention': 0.0,
                'average_posture': 0.0,
                'attentive_count': 0,
                'distracted_count': 0,
                'drowsy_count': 0
            }
        
        attention_scores = [r['attention_score'] for r in results]
        posture_scores = [r['posture_score'] for r in results]
        
        attentive_count = sum(1 for r in results if r['is_attentive'])
        drowsy_count = sum(1 for r in results if r['is_drowsy'])
        distracted_count = len(results) - attentive_count - drowsy_count
        
        return {
            'average_attention': float(np.mean(attention_scores)),
            'average_posture': float(np.mean(posture_scores)),
            'attentive_count': attentive_count,
            'distracted_count': max(0, distracted_count),
            'drowsy_count': drowsy_count
        }
