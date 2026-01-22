"""
Monitoring Pipeline
Orchestrates the live monitoring process with all AI components
"""

import numpy as np
import cv2
import time
import asyncio
import threading
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime
from loguru import logger

from models import (
    PersonDetector,
    FaceDetector,
    PostureGazeAnalyzer,
    AttentionState,
    PostureState
)
from trackers import ByteTracker, STrack


@dataclass
class TrackMetrics:
    """Metrics for a single track during a session."""
    track_id: int
    student_id: Optional[str] = None
    student_name: Optional[str] = None
    
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    
    attention_scores: List[float] = field(default_factory=list)
    posture_scores: List[float] = field(default_factory=list)
    
    phone_usage_count: int = 0
    distraction_count: int = 0
    looking_away_count: int = 0
    
    # Recent state for event detection
    last_attention_state: str = "unknown"
    last_posture_state: str = "unknown"
    phone_detected_frames: int = 0


@dataclass
class SessionMetrics:
    """Aggregated metrics for a monitoring session."""
    session_id: str
    start_time: datetime
    
    frame_count: int = 0
    fps: float = 0
    
    current_student_count: int = 0
    peak_student_count: int = 0
    
    attention_timeline: List[Dict] = field(default_factory=list)
    track_metrics: Dict[int, TrackMetrics] = field(default_factory=dict)
    
    # Event queue
    pending_events: List[Dict] = field(default_factory=list)


class MonitoringPipeline:
    """
    Main monitoring pipeline that orchestrates:
    - Person detection (YOLO)
    - Tracking (ByteTrack)
    - Face detection and recognition (InsightFace)
    - Pose estimation (MediaPipe)
    - Gaze estimation (MediaPipe Face Mesh)
    - Event generation
    """
    
    def __init__(
        self,
        target_fps: int = 8,
        known_embeddings: List[Dict] = None,
        on_event: Callable = None,
        on_frame: Callable = None
    ):
        """
        Initialize monitoring pipeline.
        
        Args:
            target_fps: Target inference rate
            known_embeddings: List of {student_id, student_name, embedding}
            on_event: Callback for events (async or sync)
            on_frame: Callback for processed frames (async or sync)
        """
        self.target_fps = target_fps
        self.frame_interval = 1.0 / target_fps
        
        self.known_embeddings = known_embeddings or []
        self.on_event = on_event
        self.on_frame = on_frame
        
        # Models
        self.person_detector = PersonDetector()
        self.face_detector = FaceDetector()
        self.pose_gaze_analyzer = PostureGazeAnalyzer()
        self.tracker = ByteTracker(
            track_thresh=0.5,
            track_buffer=30,
            match_thresh=0.8
        )
        
        # State
        self.is_running = False
        self.session_metrics: Optional[SessionMetrics] = None
        self.session_id: Optional[str] = None
        
        # Processing timing
        self._last_frame_time = 0
        self._frame_times = deque(maxlen=30)
        
        # Recognition cooldown per track
        self._recognition_cooldown: Dict[int, float] = {}
        self._recognition_interval = 2.0  # Seconds between recognition attempts
        
        # Event generation thresholds
        self.attention_high_threshold = 0.7
        self.attention_low_threshold = 0.4
        self.phone_detection_frames = 3  # Consecutive frames to confirm phone
        self.posture_poor_threshold = 0.5
    
    def initialize(self):
        """Initialize all models."""
        logger.info("Initializing monitoring pipeline models...")
        
        try:
            self.person_detector.initialize()
            self.face_detector.initialize()
            self.pose_gaze_analyzer.initialize()
            logger.info("All models initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    def start_session(self, session_id: str):
        """Start a new monitoring session."""
        self.session_id = session_id
        self.is_running = True
        self.tracker.reset()
        
        self.session_metrics = SessionMetrics(
            session_id=session_id,
            start_time=datetime.now()
        )
        
        self._recognition_cooldown.clear()
        
        logger.info(f"Monitoring session started: {session_id}")
    
    def stop_session(self) -> Dict:
        """Stop the current session and return final metrics."""
        self.is_running = False
        
        if self.session_metrics is None:
            return {}
        
        # Compile final analytics
        analytics = self._compile_session_analytics()
        
        session_id = self.session_id
        self.session_id = None
        self.session_metrics = None
        
        logger.info(f"Monitoring session stopped: {session_id}")
        
        return analytics
    
    def update_known_embeddings(self, embeddings: List[Dict]):
        """Update the list of known student embeddings."""
        self.known_embeddings = embeddings
        logger.info(f"Updated known embeddings: {len(embeddings)} students")
    
    def process_frame_sync(self, frame: np.ndarray) -> Dict:
        """
        Process a single frame synchronously (simplified version).
        Doesn't require session to be started.
        
        Args:
            frame: BGR image from camera
        
        Returns:
            Dictionary with detections, metrics, and events
        """
        result = {
            'person_count': 0,
            'face_count': 0,
            'average_attention': 0.5,
            'phone_count': 0,
            'distraction_count': 0,
            'students': [],
            'events': []
        }
        
        try:
            # === Step 1: Person Detection ===
            detections = self.person_detector.detect(frame)
            persons = detections['persons']
            objects = detections['objects']
            
            result['person_count'] = len(persons)
            
            # === Step 2: Phone Detection ===
            phones = [obj for obj in objects if obj.get('class_name') == 'phone']
            result['phone_count'] = len(phones)
            
            # === Step 3: Face Detection ===
            faces = self.face_detector.detect_faces(frame)
            result['face_count'] = len(faces)
            
            # === Step 4: Attention Analysis ===
            attention_scores = []
            students = []
            
            for i, person in enumerate(persons):
                bbox = person['bbox']
                
                # Get person ROI
                x1, y1, x2, y2 = [int(c) for c in bbox]
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                
                if x2 > x1 and y2 > y1:
                    person_roi = frame[y1:y2, x1:x2]
                    
                    # Analyze attention
                    analysis = self.pose_gaze_analyzer.analyze(person_roi, bbox)
                    attention_score = analysis.get('attention_score', 0.5)
                    attention_scores.append(attention_score)
                    
                    students.append({
                        'trackId': i + 1,
                        'name': f'Person {i + 1}',
                        'attention': round(attention_score * 100, 1),
                        'isAttentive': analysis.get('is_attentive', True),
                        'lookingAway': analysis.get('attention_state') == 'distracted',
                        'phoneDetected': False,  # Will be updated below
                        'poorPosture': analysis.get('posture_state') == 'slouching'
                    })
            
            # Associate phones with people
            for phone in phones:
                phone_bbox = phone['bbox']
                phone_center = [(phone_bbox[0] + phone_bbox[2]) / 2, 
                               (phone_bbox[1] + phone_bbox[3]) / 2]
                
                # Find nearest person
                for student in students:
                    # Mark as phone detected if phone is nearby
                    student['phoneDetected'] = True
                    result['distraction_count'] += 1
                    break
            
            # Calculate average attention
            if attention_scores:
                result['average_attention'] = sum(attention_scores) / len(attention_scores)
            
            result['students'] = students
            
            # Generate events for significant occurrences
            if len(phones) > 0:
                result['events'].append({
                    'eventType': 'phone_detected',
                    'timestamp': datetime.now().isoformat(),
                    'details': {'count': len(phones)}
                })
            
            low_attention_count = sum(1 for s in students if s['attention'] < 50)
            if low_attention_count > len(students) / 2 and len(students) > 0:
                result['events'].append({
                    'eventType': 'attention_drop',
                    'timestamp': datetime.now().isoformat(),
                    'details': {'lowAttentionCount': low_attention_count}
                })
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            result['error'] = str(e)
        
        return result
    
    async def process_frame(self, frame: np.ndarray) -> Dict:
        """
        Process a single frame through the pipeline.
        
        Args:
            frame: BGR image from camera
        
        Returns:
            Dictionary with detections, tracks, metrics, and events
        """
        if not self.is_running:
            return {'error': 'Session not running'}
        
        start_time = time.time()
        
        # Track FPS
        self._frame_times.append(start_time - self._last_frame_time)
        self._last_frame_time = start_time
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'session_id': self.session_id,
            'detections': [],
            'tracks': [],
            'metrics': {},
            'events': []
        }
        
        try:
            # === Step 1: Person Detection ===
            detections = self.person_detector.detect(frame)
            persons = detections['persons']
            objects = detections['objects']
            
            # === Step 2: Tracking ===
            track_detections = [
                {'bbox': p['bbox'], 'score': p['score'], 'class_id': 0}
                for p in persons
            ]
            active_tracks = self.tracker.update(track_detections)
            
            # === Step 3: Phone Detection ===
            phone_associations = self.person_detector.detect_phones_near_persons(
                persons, objects
            )
            phone_track_ids = set()
            
            # === Step 4: Process Each Track ===
            track_results = []
            events = []
            
            for track in active_tracks:
                track_data = await self._process_track(
                    frame, track, phone_associations, persons
                )
                track_results.append(track_data)
                
                # Collect events
                if track_data.get('events'):
                    events.extend(track_data['events'])
            
            # === Step 5: Update Session Metrics ===
            self._update_session_metrics(track_results)
            
            # Build result
            result['detections'] = {
                'persons': len(persons),
                'objects': [{'class': o['class_name'], 'bbox': o['bbox']} for o in objects]
            }
            result['tracks'] = track_results
            result['metrics'] = {
                'student_count': len(active_tracks),
                'average_attention': self._calculate_average_attention(track_results),
                'fps': self._calculate_fps()
            }
            result['events'] = events
            
            # === Step 6: Callbacks ===
            # Queue events
            if events and self.on_event:
                for event in events:
                    try:
                        if asyncio.iscoroutinefunction(self.on_event):
                            await self.on_event(event)
                        else:
                            self.on_event(event)
                    except Exception as e:
                        logger.error(f"Event callback error: {e}")
            
            # Frame callback
            if self.on_frame:
                try:
                    if asyncio.iscoroutinefunction(self.on_frame):
                        await self.on_frame(result)
                    else:
                        self.on_frame(result)
                except Exception as e:
                    logger.error(f"Frame callback error: {e}")
            
        except Exception as e:
            logger.error(f"Frame processing error: {e}")
            result['error'] = str(e)
        
        result['processing_time_ms'] = (time.time() - start_time) * 1000
        
        return result
    
    async def _process_track(
        self, 
        frame: np.ndarray, 
        track: STrack,
        phone_associations: List,
        persons: List[Dict]
    ) -> Dict:
        """Process a single track for face, pose, gaze, and events."""
        
        track_data = {
            'track_id': track.track_id,
            'bbox': track.tlbr.tolist(),
            'score': track.score,
            'student_id': track.student_id,
            'student_name': None,
            'attention': None,
            'posture': None,
            'phone_detected': False,
            'events': []
        }
        
        # Get or create track metrics
        if track.track_id not in self.session_metrics.track_metrics:
            self.session_metrics.track_metrics[track.track_id] = TrackMetrics(
                track_id=track.track_id
            )
            # New track event
            track_data['events'].append({
                'eventType': 'student_entered',
                'trackId': track.track_id,
                'confidence': track.score,
                'timestamp': datetime.now().isoformat()
            })
        
        metrics = self.session_metrics.track_metrics[track.track_id]
        metrics.last_seen = datetime.now()
        
        # Extract person region
        x1, y1, x2, y2 = [int(c) for c in track.tlbr]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
        
        if x2 <= x1 or y2 <= y1:
            return track_data
        
        person_roi = frame[y1:y2, x1:x2]
        
        # === Face Recognition (with cooldown) ===
        current_time = time.time()
        cooldown = self._recognition_cooldown.get(track.track_id, 0)
        
        if not track.student_id and current_time - cooldown > self._recognition_interval:
            face_result = await self._try_face_recognition(person_roi)
            
            if face_result:
                track.student_id = face_result['student_id']
                metrics.student_id = face_result['student_id']
                metrics.student_name = face_result.get('student_name')
                track_data['student_id'] = face_result['student_id']
                track_data['student_name'] = face_result.get('student_name')
            
            self._recognition_cooldown[track.track_id] = current_time
        else:
            track_data['student_id'] = track.student_id
            track_data['student_name'] = metrics.student_name
        
        # === Pose and Gaze Analysis ===
        analysis = self.pose_gaze_analyzer.analyze(person_roi)
        
        if analysis['gaze']:
            track_data['attention'] = analysis['gaze']
            attention_score = analysis['gaze']['score']
            metrics.attention_scores.append(attention_score)
            
            # Generate attention events
            attention_events = self._check_attention_events(
                track, metrics, analysis['gaze']
            )
            track_data['events'].extend(attention_events)
        
        if analysis['pose']:
            track_data['posture'] = analysis['pose']
            posture_score = analysis['pose']['score']
            metrics.posture_scores.append(posture_score)
            
            # Generate posture events
            posture_events = self._check_posture_events(
                track, metrics, analysis['pose']
            )
            track_data['events'].extend(posture_events)
        
        # === Phone Detection ===
        person_has_phone = any(
            idx == track.track_id or self._track_matches_person(track, persons[idx])
            for idx, _ in phone_associations
            if idx < len(persons)
        )
        
        if person_has_phone:
            metrics.phone_detected_frames += 1
        else:
            metrics.phone_detected_frames = max(0, metrics.phone_detected_frames - 1)
        
        if metrics.phone_detected_frames >= self.phone_detection_frames:
            track_data['phone_detected'] = True
            
            # Phone usage event
            phone_events = self._check_phone_events(track, metrics)
            track_data['events'].extend(phone_events)
        
        return track_data
    
    def _track_matches_person(self, track: STrack, person: Dict) -> bool:
        """Check if track bbox matches person detection."""
        from trackers.bytetrack import bbox_iou
        return bbox_iou(track.tlbr, np.array(person['bbox'])) > 0.5
    
    async def _try_face_recognition(self, roi: np.ndarray) -> Optional[Dict]:
        """Try to recognize face in ROI."""
        if len(self.known_embeddings) == 0:
            return None
        
        try:
            faces = self.face_detector.detect_faces(roi)
            
            if len(faces) == 0 or faces[0]['embedding'] is None:
                return None
            
            embedding = np.array(faces[0]['embedding'])
            match = self.face_detector.match_embedding(
                embedding, 
                self.known_embeddings,
                threshold=0.4
            )
            
            return match
        except Exception as e:
            logger.debug(f"Face recognition error: {e}")
            return None
    
    def _check_attention_events(
        self, 
        track: STrack, 
        metrics: TrackMetrics,
        gaze_data: Dict
    ) -> List[Dict]:
        """Check for attention-related events."""
        events = []
        score = gaze_data['score']
        state = gaze_data['state']
        
        timestamp = datetime.now().isoformat()
        
        # State transition events
        if metrics.last_attention_state != state:
            if state == 'focused' and score >= self.attention_high_threshold:
                events.append({
                    'eventType': 'attention_high',
                    'trackId': track.track_id,
                    'studentId': track.student_id,
                    'confidence': score,
                    'timestamp': timestamp,
                    'data': {
                        'gazeDirection': {
                            'yaw': gaze_data['yaw'],
                            'pitch': gaze_data['pitch']
                        }
                    }
                })
            elif state == 'distracted':
                metrics.distraction_count += 1
                events.append({
                    'eventType': 'attention_low',
                    'trackId': track.track_id,
                    'studentId': track.student_id,
                    'confidence': 1 - score,
                    'timestamp': timestamp,
                    'data': {
                        'gazeDirection': {
                            'yaw': gaze_data['yaw'],
                            'pitch': gaze_data['pitch']
                        }
                    }
                })
            elif state == 'drowsy':
                events.append({
                    'eventType': 'drowsiness_detected',
                    'trackId': track.track_id,
                    'studentId': track.student_id,
                    'confidence': 1 - gaze_data['eye_aspect_ratio'],
                    'timestamp': timestamp,
                    'data': {
                        'eyeAspectRatio': gaze_data['eye_aspect_ratio']
                    }
                })
        
        metrics.last_attention_state = state
        
        return events
    
    def _check_posture_events(
        self,
        track: STrack,
        metrics: TrackMetrics,
        pose_data: Dict
    ) -> List[Dict]:
        """Check for posture-related events."""
        events = []
        state = pose_data['state']
        score = pose_data['score']
        
        timestamp = datetime.now().isoformat()
        
        if metrics.last_posture_state != state:
            if state in ['slouching', 'leaning']:
                events.append({
                    'eventType': 'posture_poor',
                    'trackId': track.track_id,
                    'studentId': track.student_id,
                    'confidence': 1 - score,
                    'timestamp': timestamp,
                    'data': {
                        'postureScore': score,
                        'postureState': state
                    }
                })
            elif state == 'good' and metrics.last_posture_state in ['slouching', 'leaning']:
                events.append({
                    'eventType': 'posture_good',
                    'trackId': track.track_id,
                    'studentId': track.student_id,
                    'confidence': score,
                    'timestamp': timestamp
                })
        
        metrics.last_posture_state = state
        
        return events
    
    def _check_phone_events(
        self,
        track: STrack,
        metrics: TrackMetrics
    ) -> List[Dict]:
        """Check for phone usage events."""
        events = []
        timestamp = datetime.now().isoformat()
        
        # Only trigger if this is a new phone detection
        if metrics.phone_detected_frames == self.phone_detection_frames:
            metrics.phone_usage_count += 1
            events.append({
                'eventType': 'phone_detected',
                'trackId': track.track_id,
                'studentId': track.student_id,
                'confidence': 0.8,
                'timestamp': timestamp
            })
        
        return events
    
    def _update_session_metrics(self, track_results: List[Dict]):
        """Update aggregated session metrics."""
        if self.session_metrics is None:
            return
        
        self.session_metrics.frame_count += 1
        self.session_metrics.current_student_count = len(track_results)
        self.session_metrics.peak_student_count = max(
            self.session_metrics.peak_student_count,
            len(track_results)
        )
        
        # Update attention timeline
        if track_results:
            avg_attention = self._calculate_average_attention(track_results)
            self.session_metrics.attention_timeline.append({
                'timestamp': datetime.now().isoformat(),
                'value': avg_attention,
                'student_count': len(track_results)
            })
    
    def _calculate_average_attention(self, track_results: List[Dict]) -> float:
        """Calculate average attention score across all tracks."""
        attention_scores = [
            t['attention']['score'] 
            for t in track_results 
            if t.get('attention') and t['attention'].get('score') is not None
        ]
        
        if not attention_scores:
            return 0
        
        return sum(attention_scores) / len(attention_scores)
    
    def _calculate_fps(self) -> float:
        """Calculate current processing FPS."""
        if len(self._frame_times) < 2:
            return 0
        
        avg_interval = sum(self._frame_times) / len(self._frame_times)
        return 1.0 / avg_interval if avg_interval > 0 else 0
    
    def _compile_session_analytics(self) -> Dict:
        """Compile final session analytics."""
        if self.session_metrics is None:
            return {}
        
        metrics = self.session_metrics
        
        # Compile per-student metrics
        student_metrics = []
        for track_id, track_metrics in metrics.track_metrics.items():
            student_metrics.append({
                'trackId': track_id,
                'studentId': track_metrics.student_id,
                'name': track_metrics.student_name,
                'averageAttention': (
                    sum(track_metrics.attention_scores) / len(track_metrics.attention_scores)
                    if track_metrics.attention_scores else None
                ),
                'distractionCount': track_metrics.distraction_count,
                'phoneUsageCount': track_metrics.phone_usage_count,
                'firstSeen': track_metrics.first_seen.isoformat(),
                'lastSeen': track_metrics.last_seen.isoformat(),
                'totalTimePresent': (
                    track_metrics.last_seen - track_metrics.first_seen
                ).total_seconds()
            })
        
        # Calculate overall metrics
        all_attention = []
        for tm in metrics.track_metrics.values():
            all_attention.extend(tm.attention_scores)
        
        return {
            'attention': {
                'average': sum(all_attention) / len(all_attention) if all_attention else 0,
                'min': min(all_attention) if all_attention else 0,
                'max': max(all_attention) if all_attention else 0
            },
            'peakStudentCount': metrics.peak_student_count,
            'averageStudentCount': (
                sum(t['student_count'] for t in metrics.attention_timeline) / 
                len(metrics.attention_timeline)
                if metrics.attention_timeline else 0
            ),
            'studentMetrics': student_metrics,
            'totalFrames': metrics.frame_count,
            'averageFps': self._calculate_fps()
        }
    
    def get_current_metrics(self) -> Dict:
        """Get current session metrics snapshot."""
        if self.session_metrics is None:
            return {}
        
        return {
            'session_id': self.session_id,
            'is_running': self.is_running,
            'current_student_count': self.session_metrics.current_student_count,
            'peak_student_count': self.session_metrics.peak_student_count,
            'frame_count': self.session_metrics.frame_count,
            'fps': self._calculate_fps(),
            'tracker_stats': self.tracker.get_stats()
        }
