"""
Models Module
"""

# Try to use simplified detection (no InsightFace dependency)
try:
    from .detection_simple import (
        PersonDetector,
        FaceDetector,
        FaceEnrollmentManager,
        get_yolo_model,
        get_face_app
    )
except ImportError:
    # Fall back to original detection
    from .detection import (
        PersonDetector,
        FaceDetector,
        FaceEnrollmentManager,
        get_yolo_model,
        get_face_app
    )

# Try to use simplified pose/gaze (no MediaPipe solutions dependency)
try:
    from .pose_gaze_simple import (
        PoseEstimator,
        GazeEstimator,
        PostureGazeAnalyzer,
        PostureState,
        AttentionState,
        PoseResult,
        GazeResult
    )
except ImportError:
    from .pose_gaze import (
        PoseEstimator,
        GazeEstimator,
        PostureGazeAnalyzer,
        PostureState,
        AttentionState,
        PoseResult,
        GazeResult
    )

__all__ = [
    'PersonDetector',
    'FaceDetector',
    'FaceEnrollmentManager',
    'get_yolo_model',
    'get_face_app',
    'PoseEstimator',
    'GazeEstimator',
    'PostureGazeAnalyzer',
    'PostureState',
    'AttentionState',
    'PoseResult',
    'GazeResult'
]
