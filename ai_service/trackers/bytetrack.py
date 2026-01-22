"""
ByteTrack Implementation for Single-Camera Tracking
Based on ByteTrack: Multi-Object Tracking by Associating Every Detection Box
"""

import numpy as np
from collections import defaultdict
from scipy.optimize import linear_sum_assignment
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import time


@dataclass
class TrackState:
    """Track state enumeration."""
    NEW = 0
    TRACKED = 1
    LOST = 2
    REMOVED = 3


@dataclass 
class STrack:
    """Single object tracking representation."""
    
    track_id: int = 0
    bbox: np.ndarray = field(default_factory=lambda: np.zeros(4))  # x1, y1, x2, y2
    score: float = 0.0
    class_id: int = 0
    
    # Kalman filter state
    mean: np.ndarray = field(default_factory=lambda: np.zeros(8))
    covariance: np.ndarray = field(default_factory=lambda: np.eye(8))
    
    # Track management
    state: int = TrackState.NEW
    is_activated: bool = False
    frame_id: int = 0
    start_frame: int = 0
    tracklet_len: int = 0
    
    # Additional data
    features: Optional[np.ndarray] = None
    student_id: Optional[str] = None
    
    _next_id: int = 0
    
    def __post_init__(self):
        if self.track_id == 0:
            STrack._next_id += 1
            self.track_id = STrack._next_id
    
    @staticmethod
    def reset_id():
        """Reset track ID counter."""
        STrack._next_id = 0
    
    def activate(self, frame_id: int):
        """Activate a new track."""
        self.frame_id = frame_id
        self.start_frame = frame_id
        self.state = TrackState.TRACKED
        self.is_activated = True
        self.tracklet_len = 0
    
    def re_activate(self, new_track: 'STrack', frame_id: int):
        """Re-activate a lost track."""
        self.bbox = new_track.bbox
        self.score = new_track.score
        self.mean = new_track.mean
        self.covariance = new_track.covariance
        self.frame_id = frame_id
        self.tracklet_len = 0
        self.state = TrackState.TRACKED
        self.is_activated = True
        if new_track.features is not None:
            self.features = new_track.features
    
    def update(self, new_track: 'STrack', frame_id: int):
        """Update a matched track."""
        self.frame_id = frame_id
        self.bbox = new_track.bbox
        self.score = new_track.score
        self.tracklet_len += 1
        self.state = TrackState.TRACKED
        self.is_activated = True
        if new_track.features is not None:
            self.features = new_track.features
    
    def mark_lost(self):
        """Mark track as lost."""
        self.state = TrackState.LOST
    
    def mark_removed(self):
        """Mark track as removed."""
        self.state = TrackState.REMOVED
    
    @property
    def tlwh(self) -> np.ndarray:
        """Get bbox in (top-left x, top-left y, width, height) format."""
        ret = self.bbox.copy()
        ret[2:] -= ret[:2]
        return ret
    
    @property
    def tlbr(self) -> np.ndarray:
        """Get bbox in (top-left x, top-left y, bottom-right x, bottom-right y) format."""
        return self.bbox.copy()
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get bbox center."""
        return (
            (self.bbox[0] + self.bbox[2]) / 2,
            (self.bbox[1] + self.bbox[3]) / 2
        )


class KalmanFilter:
    """Simple Kalman filter for tracking bounding boxes."""
    
    def __init__(self):
        # State: [cx, cy, w, h, vx, vy, vw, vh]
        self.ndim = 4
        self.dt = 1.0
        
        # Motion model
        self._motion_mat = np.eye(8)
        for i in range(4):
            self._motion_mat[i, i + 4] = self.dt
        
        # Observation model
        self._update_mat = np.eye(4, 8)
        
        # Process noise
        self._std_weight_position = 1.0 / 20
        self._std_weight_velocity = 1.0 / 160
    
    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Initialize track from first detection."""
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.concatenate([mean_pos, mean_vel])
        
        std = [
            2 * self._std_weight_position * measurement[2],
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[2],
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[2],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[2],
            10 * self._std_weight_velocity * measurement[3]
        ]
        covariance = np.diag(np.square(std))
        
        return mean, covariance
    
    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Run Kalman filter prediction step."""
        std = [
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_velocity * mean[2],
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[2],
            self._std_weight_velocity * mean[3]
        ]
        motion_cov = np.diag(np.square(std))
        
        mean = self._motion_mat @ mean
        covariance = self._motion_mat @ covariance @ self._motion_mat.T + motion_cov
        
        return mean, covariance
    
    def update(self, mean: np.ndarray, covariance: np.ndarray, 
               measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Run Kalman filter update step."""
        std = [
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[2],
            self._std_weight_position * mean[3]
        ]
        innovation_cov = np.diag(np.square(std))
        
        projected_mean = self._update_mat @ mean
        projected_cov = self._update_mat @ covariance @ self._update_mat.T + innovation_cov
        
        kalman_gain = covariance @ self._update_mat.T @ np.linalg.inv(projected_cov)
        innovation = measurement - projected_mean
        
        new_mean = mean + kalman_gain @ innovation
        new_covariance = covariance - kalman_gain @ self._update_mat @ covariance
        
        return new_mean, new_covariance


def bbox_iou(bbox1: np.ndarray, bbox2: np.ndarray) -> float:
    """Calculate IoU between two bboxes in tlbr format."""
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])
    
    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    
    union_area = area1 + area2 - inter_area
    
    return inter_area / union_area if union_area > 0 else 0


def iou_distance(tracks: List[STrack], detections: List[STrack]) -> np.ndarray:
    """Calculate IoU distance matrix between tracks and detections."""
    if len(tracks) == 0 or len(detections) == 0:
        return np.zeros((len(tracks), len(detections)))
    
    cost_matrix = np.zeros((len(tracks), len(detections)))
    
    for i, track in enumerate(tracks):
        for j, det in enumerate(detections):
            cost_matrix[i, j] = 1 - bbox_iou(track.tlbr, det.tlbr)
    
    return cost_matrix


def linear_assignment(cost_matrix: np.ndarray, thresh: float) -> Tuple[List, List, List]:
    """Perform linear assignment with threshold."""
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))
    
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    
    matches = []
    unmatched_tracks = list(range(cost_matrix.shape[0]))
    unmatched_dets = list(range(cost_matrix.shape[1]))
    
    for row, col in zip(row_indices, col_indices):
        if cost_matrix[row, col] < thresh:
            matches.append((row, col))
            if row in unmatched_tracks:
                unmatched_tracks.remove(row)
            if col in unmatched_dets:
                unmatched_dets.remove(col)
    
    return matches, unmatched_tracks, unmatched_dets


class ByteTracker:
    """
    ByteTrack multi-object tracker.
    Handles association of detections across frames for single camera.
    """
    
    def __init__(
        self,
        track_thresh: float = 0.5,
        track_buffer: int = 30,
        match_thresh: float = 0.8,
        min_box_area: int = 100
    ):
        self.track_thresh = track_thresh
        self.track_buffer = track_buffer
        self.match_thresh = match_thresh
        self.min_box_area = min_box_area
        
        self.kalman_filter = KalmanFilter()
        
        self.tracked_tracks: List[STrack] = []
        self.lost_tracks: List[STrack] = []
        self.removed_tracks: List[STrack] = []
        
        self.frame_id = 0
    
    def reset(self):
        """Reset tracker state."""
        self.tracked_tracks = []
        self.lost_tracks = []
        self.removed_tracks = []
        self.frame_id = 0
        STrack.reset_id()
    
    def update(self, detections: List[dict]) -> List[STrack]:
        """
        Update tracker with new detections.
        
        Args:
            detections: List of detection dicts with keys:
                - bbox: [x1, y1, x2, y2]
                - score: confidence score
                - class_id: detection class
                - features: optional embedding features
        
        Returns:
            List of active tracks
        """
        self.frame_id += 1
        
        # Filter small detections
        valid_dets = []
        for det in detections:
            bbox = np.array(det['bbox'])
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if area >= self.min_box_area:
                valid_dets.append(det)
        
        # Separate high and low confidence detections
        high_dets = []
        low_dets = []
        
        for det in valid_dets:
            track = STrack(
                bbox=np.array(det['bbox']),
                score=det['score'],
                class_id=det.get('class_id', 0),
                features=det.get('features')
            )
            
            # Initialize Kalman filter
            cx = (det['bbox'][0] + det['bbox'][2]) / 2
            cy = (det['bbox'][1] + det['bbox'][3]) / 2
            w = det['bbox'][2] - det['bbox'][0]
            h = det['bbox'][3] - det['bbox'][1]
            measurement = np.array([cx, cy, w, h])
            track.mean, track.covariance = self.kalman_filter.initiate(measurement)
            
            if det['score'] >= self.track_thresh:
                high_dets.append(track)
            else:
                low_dets.append(track)
        
        # Predict track positions
        for track in self.tracked_tracks:
            track.mean, track.covariance = self.kalman_filter.predict(
                track.mean, track.covariance
            )
            # Update bbox from predicted state
            cx, cy, w, h = track.mean[:4]
            track.bbox = np.array([cx - w/2, cy - h/2, cx + w/2, cy + h/2])
        
        for track in self.lost_tracks:
            track.mean, track.covariance = self.kalman_filter.predict(
                track.mean, track.covariance
            )
        
        # === First association with high confidence detections ===
        unconfirmed = [t for t in self.tracked_tracks if not t.is_activated]
        tracked = [t for t in self.tracked_tracks if t.is_activated]
        
        # Associate tracked tracks with high confidence detections
        cost_matrix = iou_distance(tracked, high_dets)
        matches, unmatched_tracks, unmatched_dets = linear_assignment(
            cost_matrix, self.match_thresh
        )
        
        # Update matched tracks
        for track_idx, det_idx in matches:
            track = tracked[track_idx]
            det = high_dets[det_idx]
            
            # Kalman update
            cx = (det.bbox[0] + det.bbox[2]) / 2
            cy = (det.bbox[1] + det.bbox[3]) / 2
            w = det.bbox[2] - det.bbox[0]
            h = det.bbox[3] - det.bbox[1]
            measurement = np.array([cx, cy, w, h])
            track.mean, track.covariance = self.kalman_filter.update(
                track.mean, track.covariance, measurement
            )
            
            track.update(det, self.frame_id)
        
        # Remaining high confidence detections and unmatched tracks
        remaining_tracked = [tracked[i] for i in unmatched_tracks]
        remaining_high_dets = [high_dets[i] for i in unmatched_dets]
        
        # === Second association with low confidence detections ===
        cost_matrix = iou_distance(remaining_tracked, low_dets)
        matches, unmatched_tracks_2, _ = linear_assignment(cost_matrix, 0.5)
        
        for track_idx, det_idx in matches:
            track = remaining_tracked[track_idx]
            det = low_dets[det_idx]
            track.update(det, self.frame_id)
        
        # Mark remaining unmatched tracks as lost
        for idx in unmatched_tracks_2:
            track = remaining_tracked[idx]
            if track.state != TrackState.LOST:
                track.mark_lost()
                self.lost_tracks.append(track)
        
        # === Third association: lost tracks with remaining high detections ===
        cost_matrix = iou_distance(self.lost_tracks, remaining_high_dets)
        matches, unmatched_lost, unmatched_high = linear_assignment(cost_matrix, 0.7)
        
        for track_idx, det_idx in matches:
            track = self.lost_tracks[track_idx]
            det = remaining_high_dets[det_idx]
            track.re_activate(det, self.frame_id)
        
        # Remove lost tracks that exceeded buffer
        removed_lost = []
        for track in self.lost_tracks:
            if self.frame_id - track.frame_id > self.track_buffer:
                track.mark_removed()
                removed_lost.append(track)
        
        self.lost_tracks = [t for t in self.lost_tracks 
                           if t.state == TrackState.LOST and t not in removed_lost]
        
        # === Initialize new tracks from unmatched high confidence detections ===
        new_tracks = []
        for idx in unmatched_high:
            det = remaining_high_dets[idx]
            if det.score >= self.track_thresh:
                det.activate(self.frame_id)
                new_tracks.append(det)
        
        # Update track lists
        self.tracked_tracks = [t for t in self.tracked_tracks 
                              if t.state == TrackState.TRACKED]
        self.tracked_tracks.extend(new_tracks)
        
        # Return all active tracks
        active_tracks = [t for t in self.tracked_tracks if t.is_activated]
        
        return active_tracks
    
    def get_track_by_id(self, track_id: int) -> Optional[STrack]:
        """Get track by ID."""
        for track in self.tracked_tracks + self.lost_tracks:
            if track.track_id == track_id:
                return track
        return None
    
    def assign_student_id(self, track_id: int, student_id: str):
        """Assign student ID to a track."""
        track = self.get_track_by_id(track_id)
        if track:
            track.student_id = student_id
    
    def get_stats(self) -> dict:
        """Get tracker statistics."""
        return {
            'frame_id': self.frame_id,
            'tracked_count': len(self.tracked_tracks),
            'lost_count': len(self.lost_tracks),
            'total_tracks_created': STrack._next_id
        }
