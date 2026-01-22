"""
Pose and Gaze Estimation Module
Uses MediaPipe for pose estimation and gaze direction
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import threading
from loguru import logger

# Lazy import MediaPipe
_mp_pose = None
_mp_face_mesh = None
_pose_detector = None
_face_mesh_detector = None
_models_lock = threading.Lock()


class PostureState(Enum):
    """Posture classification states."""
    GOOD = "good"
    SLOUCHING = "slouching"
    LEANING = "leaning"
    UNKNOWN = "unknown"


class AttentionState(Enum):
    """Attention classification based on gaze."""
    FOCUSED = "focused"  # Looking at instructor/board
    DISTRACTED = "distracted"  # Looking away
    DROWSY = "drowsy"  # Eyes closing
    UNKNOWN = "unknown"


@dataclass
class PoseResult:
    """Pose estimation result."""
    posture_state: PostureState
    posture_score: float  # 0-1, higher is better
    shoulder_angle: float
    head_tilt: float
    landmarks: Optional[np.ndarray] = None


@dataclass
class GazeResult:
    """Gaze estimation result."""
    attention_state: AttentionState
    attention_score: float  # 0-1, higher is more attentive
    yaw: float  # Horizontal head rotation (-90 to 90)
    pitch: float  # Vertical head rotation (-90 to 90)
    roll: float  # Head tilt
    eye_aspect_ratio: float  # For drowsiness detection
    landmarks: Optional[np.ndarray] = None


def get_pose_detector():
    """Get or initialize MediaPipe Pose detector."""
    global _mp_pose, _pose_detector
    
    if _pose_detector is None:
        with _models_lock:
            if _pose_detector is None:
                try:
                    import mediapipe as mp
                    _mp_pose = mp.solutions.pose
                    _pose_detector = _mp_pose.Pose(
                        static_image_mode=False,
                        model_complexity=1,
                        smooth_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    logger.info("MediaPipe Pose detector loaded")
                except Exception as e:
                    logger.error(f"Failed to load MediaPipe Pose: {e}")
                    raise
    
    return _pose_detector


def get_face_mesh_detector():
    """Get or initialize MediaPipe Face Mesh detector."""
    global _mp_face_mesh, _face_mesh_detector
    
    if _face_mesh_detector is None:
        with _models_lock:
            if _face_mesh_detector is None:
                try:
                    import mediapipe as mp
                    _mp_face_mesh = mp.solutions.face_mesh
                    _face_mesh_detector = _mp_face_mesh.FaceMesh(
                        static_image_mode=False,
                        max_num_faces=1,
                        refine_landmarks=True,
                        min_detection_confidence=0.5,
                        min_tracking_confidence=0.5
                    )
                    logger.info("MediaPipe Face Mesh detector loaded")
                except Exception as e:
                    logger.error(f"Failed to load MediaPipe Face Mesh: {e}")
                    raise
    
    return _face_mesh_detector


class PoseEstimator:
    """MediaPipe-based pose estimation for posture analysis."""
    
    # MediaPipe Pose landmark indices
    LEFT_SHOULDER = 11
    RIGHT_SHOULDER = 12
    LEFT_HIP = 23
    RIGHT_HIP = 24
    LEFT_EAR = 7
    RIGHT_EAR = 8
    NOSE = 0
    
    def __init__(self):
        self.detector = None
    
    def initialize(self):
        """Initialize the detector."""
        self.detector = get_pose_detector()
    
    def estimate(self, frame: np.ndarray, person_bbox: List[float] = None) -> Optional[PoseResult]:
        """
        Estimate pose for a person in the frame.
        
        Args:
            frame: BGR image
            person_bbox: Optional [x1, y1, x2, y2] to crop to person
        
        Returns:
            PoseResult or None if no pose detected
        """
        if self.detector is None:
            self.initialize()
        
        # Crop to person bbox if provided
        if person_bbox is not None:
            x1, y1, x2, y2 = [int(c) for c in person_bbox]
            frame = frame[y1:y2, x1:x2]
        
        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.detector.process(rgb_frame)
        
        if results.pose_landmarks is None:
            return None
        
        landmarks = results.pose_landmarks.landmark
        h, w = frame.shape[:2]
        
        # Extract key points
        def get_point(idx):
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h, lm.visibility])
        
        left_shoulder = get_point(self.LEFT_SHOULDER)
        right_shoulder = get_point(self.RIGHT_SHOULDER)
        left_hip = get_point(self.LEFT_HIP)
        right_hip = get_point(self.RIGHT_HIP)
        nose = get_point(self.NOSE)
        
        # Calculate shoulder angle (deviation from horizontal)
        shoulder_vec = right_shoulder[:2] - left_shoulder[:2]
        shoulder_angle = np.degrees(np.arctan2(shoulder_vec[1], shoulder_vec[0]))
        
        # Calculate spine alignment (vertical alignment)
        mid_shoulder = (left_shoulder[:2] + right_shoulder[:2]) / 2
        mid_hip = (left_hip[:2] + right_hip[:2]) / 2
        spine_vec = mid_shoulder - mid_hip
        spine_angle = np.degrees(np.arctan2(spine_vec[0], -spine_vec[1]))  # 0 = vertical
        
        # Calculate head tilt relative to shoulders
        head_to_shoulder = nose[:2] - mid_shoulder
        head_tilt = np.degrees(np.arctan2(head_to_shoulder[0], -head_to_shoulder[1]))
        
        # Classify posture
        posture_state, posture_score = self._classify_posture(
            shoulder_angle, spine_angle, head_tilt
        )
        
        # Convert landmarks to numpy array
        landmarks_array = np.array([
            [lm.x * w, lm.y * h, lm.visibility] 
            for lm in landmarks
        ])
        
        return PoseResult(
            posture_state=posture_state,
            posture_score=posture_score,
            shoulder_angle=shoulder_angle,
            head_tilt=head_tilt,
            landmarks=landmarks_array
        )
    
    def _classify_posture(
        self, 
        shoulder_angle: float, 
        spine_angle: float,
        head_tilt: float
    ) -> Tuple[PostureState, float]:
        """Classify posture based on angles."""
        score = 1.0
        
        # Penalize shoulder tilt
        shoulder_penalty = abs(shoulder_angle) / 45  # Max penalty at 45 degrees
        score -= min(0.3, shoulder_penalty * 0.3)
        
        # Penalize spine lean
        spine_penalty = abs(spine_angle) / 30  # Max penalty at 30 degrees
        score -= min(0.4, spine_penalty * 0.4)
        
        # Penalize head tilt
        head_penalty = abs(head_tilt) / 30
        score -= min(0.3, head_penalty * 0.3)
        
        score = max(0, score)
        
        # Classify
        if abs(spine_angle) > 20:
            return PostureState.LEANING, score
        elif abs(shoulder_angle) > 15 or score < 0.5:
            return PostureState.SLOUCHING, score
        else:
            return PostureState.GOOD, score


class GazeEstimator:
    """MediaPipe Face Mesh-based gaze and attention estimation."""
    
    # Face mesh landmark indices for key points
    NOSE_TIP = 1
    CHIN = 199
    LEFT_EYE_LEFT = 33
    LEFT_EYE_RIGHT = 133
    RIGHT_EYE_LEFT = 362
    RIGHT_EYE_RIGHT = 263
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374
    LEFT_MOUTH = 61
    RIGHT_MOUTH = 291
    
    # 3D model points for head pose estimation
    MODEL_POINTS = np.array([
        (0.0, 0.0, 0.0),          # Nose tip
        (0.0, -330.0, -65.0),      # Chin
        (-225.0, 170.0, -135.0),   # Left eye left corner
        (225.0, 170.0, -135.0),    # Right eye right corner
        (-150.0, -150.0, -125.0),  # Left mouth corner
        (150.0, -150.0, -125.0)    # Right mouth corner
    ], dtype=np.float64)
    
    def __init__(self, attention_yaw_threshold: float = 30, attention_pitch_threshold: float = 20):
        self.detector = None
        self.attention_yaw_threshold = attention_yaw_threshold
        self.attention_pitch_threshold = attention_pitch_threshold
        self.ear_threshold = 0.2  # Eye aspect ratio threshold for drowsiness
    
    def initialize(self):
        """Initialize the detector."""
        self.detector = get_face_mesh_detector()
    
    def estimate(self, frame: np.ndarray, face_bbox: List[float] = None) -> Optional[GazeResult]:
        """
        Estimate gaze direction and attention state.
        
        Args:
            frame: BGR image
            face_bbox: Optional [x1, y1, x2, y2] to crop to face region
        
        Returns:
            GazeResult or None if no face detected
        """
        if self.detector is None:
            self.initialize()
        
        h, w = frame.shape[:2]
        
        # Convert to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.detector.process(rgb_frame)
        
        if results.multi_face_landmarks is None or len(results.multi_face_landmarks) == 0:
            return None
        
        face_landmarks = results.multi_face_landmarks[0]
        
        # Convert landmarks to pixel coordinates
        landmarks = np.array([
            [lm.x * w, lm.y * h] 
            for lm in face_landmarks.landmark
        ])
        
        # Get key points for head pose estimation
        image_points = np.array([
            landmarks[self.NOSE_TIP],
            landmarks[self.CHIN],
            landmarks[self.LEFT_EYE_LEFT],
            landmarks[self.RIGHT_EYE_RIGHT],
            landmarks[self.LEFT_MOUTH],
            landmarks[self.RIGHT_MOUTH]
        ], dtype=np.float64)
        
        # Camera matrix approximation
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype=np.float64)
        
        dist_coeffs = np.zeros((4, 1))
        
        # Solve PnP for head pose
        success, rotation_vector, translation_vector = cv2.solvePnP(
            self.MODEL_POINTS,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return None
        
        # Convert rotation vector to Euler angles
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        yaw, pitch, roll = self._rotation_matrix_to_euler(rotation_matrix)
        
        # Calculate eye aspect ratio for drowsiness
        left_ear = self._eye_aspect_ratio(
            landmarks[self.LEFT_EYE_TOP],
            landmarks[self.LEFT_EYE_BOTTOM],
            landmarks[self.LEFT_EYE_LEFT],
            landmarks[self.LEFT_EYE_RIGHT]
        )
        right_ear = self._eye_aspect_ratio(
            landmarks[self.RIGHT_EYE_TOP],
            landmarks[self.RIGHT_EYE_BOTTOM],
            landmarks[self.RIGHT_EYE_LEFT],
            landmarks[self.RIGHT_EYE_RIGHT]
        )
        avg_ear = (left_ear + right_ear) / 2
        
        # Classify attention state
        attention_state, attention_score = self._classify_attention(
            yaw, pitch, avg_ear
        )
        
        return GazeResult(
            attention_state=attention_state,
            attention_score=attention_score,
            yaw=yaw,
            pitch=pitch,
            roll=roll,
            eye_aspect_ratio=avg_ear,
            landmarks=landmarks
        )
    
    def _rotation_matrix_to_euler(self, R: np.ndarray) -> Tuple[float, float, float]:
        """Convert rotation matrix to Euler angles (yaw, pitch, roll)."""
        sy = np.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)
        
        singular = sy < 1e-6
        
        if not singular:
            x = np.arctan2(R[2, 1], R[2, 2])
            y = np.arctan2(-R[2, 0], sy)
            z = np.arctan2(R[1, 0], R[0, 0])
        else:
            x = np.arctan2(-R[1, 2], R[1, 1])
            y = np.arctan2(-R[2, 0], sy)
            z = 0
        
        # Convert to degrees
        yaw = np.degrees(y)
        pitch = np.degrees(x)
        roll = np.degrees(z)
        
        return yaw, pitch, roll
    
    def _eye_aspect_ratio(
        self, 
        top: np.ndarray, 
        bottom: np.ndarray,
        left: np.ndarray, 
        right: np.ndarray
    ) -> float:
        """
        Calculate eye aspect ratio (EAR).
        Lower values indicate closed eyes (drowsiness).
        """
        vertical_dist = np.linalg.norm(top - bottom)
        horizontal_dist = np.linalg.norm(left - right)
        
        if horizontal_dist == 0:
            return 0
        
        return vertical_dist / horizontal_dist
    
    def _classify_attention(
        self, 
        yaw: float, 
        pitch: float, 
        ear: float
    ) -> Tuple[AttentionState, float]:
        """Classify attention state based on gaze direction and eye state."""
        
        # Check for drowsiness first
        if ear < self.ear_threshold:
            # Eyes are closing
            score = ear / self.ear_threshold  # Lower EAR = lower score
            return AttentionState.DROWSY, score
        
        # Check gaze direction
        yaw_deviation = abs(yaw)
        pitch_deviation = abs(pitch)
        
        # Calculate attention score based on deviation from center
        yaw_score = max(0, 1 - (yaw_deviation / self.attention_yaw_threshold))
        pitch_score = max(0, 1 - (pitch_deviation / self.attention_pitch_threshold))
        
        # Combined score (weighted)
        attention_score = 0.6 * yaw_score + 0.3 * pitch_score + 0.1 * min(1, ear / 0.3)
        
        if yaw_deviation > self.attention_yaw_threshold or pitch_deviation > self.attention_pitch_threshold:
            return AttentionState.DISTRACTED, attention_score
        
        return AttentionState.FOCUSED, attention_score


class PostureGazeAnalyzer:
    """Combined analyzer for posture and gaze estimation."""
    
    def __init__(self):
        self.pose_estimator = PoseEstimator()
        self.gaze_estimator = GazeEstimator()
    
    def initialize(self):
        """Initialize both estimators."""
        self.pose_estimator.initialize()
        self.gaze_estimator.initialize()
    
    def analyze(
        self, 
        frame: np.ndarray,
        person_bbox: List[float] = None,
        face_bbox: List[float] = None
    ) -> Dict:
        """
        Perform combined pose and gaze analysis.
        
        Args:
            frame: BGR image
            person_bbox: Optional person bounding box
            face_bbox: Optional face bounding box
        
        Returns:
            Dictionary with pose and gaze results
        """
        results = {
            'pose': None,
            'gaze': None,
            'combined_attention_score': 0,
            'combined_posture_score': 0
        }
        
        # Estimate pose
        pose_result = self.pose_estimator.estimate(frame, person_bbox)
        if pose_result:
            results['pose'] = {
                'state': pose_result.posture_state.value,
                'score': pose_result.posture_score,
                'shoulder_angle': pose_result.shoulder_angle,
                'head_tilt': pose_result.head_tilt
            }
            results['combined_posture_score'] = pose_result.posture_score
        
        # Estimate gaze
        gaze_result = self.gaze_estimator.estimate(frame, face_bbox)
        if gaze_result:
            results['gaze'] = {
                'state': gaze_result.attention_state.value,
                'score': gaze_result.attention_score,
                'yaw': gaze_result.yaw,
                'pitch': gaze_result.pitch,
                'roll': gaze_result.roll,
                'eye_aspect_ratio': gaze_result.eye_aspect_ratio
            }
            results['combined_attention_score'] = gaze_result.attention_score
        
        return results
