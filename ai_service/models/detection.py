"""
Detection Models Module
Handles YOLOv8 for person/object detection and InsightFace for face detection/recognition
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import threading
from loguru import logger

# Lazy imports to handle missing dependencies gracefully
_yolo_model = None
_face_app = None
_models_lock = threading.Lock()


def get_yolo_model():
    """Get or initialize YOLO model (lazy loading)."""
    global _yolo_model
    
    if _yolo_model is None:
        with _models_lock:
            if _yolo_model is None:
                try:
                    from ultralytics import YOLO
                    from config import settings
                    
                    model_path = settings.yolo_model
                    logger.info(f"Loading YOLO model: {model_path}")
                    _yolo_model = YOLO(model_path)
                    logger.info("YOLO model loaded successfully")
                except Exception as e:
                    logger.error(f"Failed to load YOLO model: {e}")
                    raise
    
    return _yolo_model


def get_face_app():
    """Get or initialize InsightFace app (lazy loading)."""
    global _face_app
    
    if _face_app is None:
        with _models_lock:
            if _face_app is None:
                try:
                    import insightface
                    from insightface.app import FaceAnalysis
                    from config import settings
                    
                    logger.info("Loading InsightFace model...")
                    _face_app = FaceAnalysis(
                        name='buffalo_l',
                        root=str(settings.models_dir),
                        providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
                    )
                    _face_app.prepare(ctx_id=0, det_size=(640, 640))
                    logger.info("InsightFace model loaded successfully")
                except Exception as e:
                    logger.error(f"Failed to load InsightFace model: {e}")
                    raise
    
    return _face_app


class PersonDetector:
    """YOLOv8-based person and object detector."""
    
    # COCO class IDs
    PERSON_CLASS = 0
    PHONE_CLASS = 67  # cell phone
    LAPTOP_CLASS = 63
    BOOK_CLASS = 73
    
    RELEVANT_CLASSES = {
        PERSON_CLASS: 'person',
        PHONE_CLASS: 'phone',
        LAPTOP_CLASS: 'laptop',
        BOOK_CLASS: 'book'
    }
    
    def __init__(self, conf_threshold: float = 0.5):
        self.conf_threshold = conf_threshold
        self.model = None
    
    def initialize(self):
        """Initialize the model."""
        self.model = get_yolo_model()
    
    def detect(self, frame: np.ndarray) -> Dict[str, List[dict]]:
        """
        Detect persons and relevant objects in frame.
        
        Args:
            frame: BGR image (H, W, 3)
        
        Returns:
            Dictionary with 'persons' and 'objects' lists
        """
        if self.model is None:
            self.initialize()
        
        results = self.model(frame, verbose=False, conf=self.conf_threshold)[0]
        
        detections = {
            'persons': [],
            'objects': []
        }
        
        for box in results.boxes:
            class_id = int(box.cls[0])
            
            if class_id not in self.RELEVANT_CLASSES:
                continue
            
            bbox = box.xyxy[0].cpu().numpy()
            confidence = float(box.conf[0])
            
            detection = {
                'bbox': bbox.tolist(),  # [x1, y1, x2, y2]
                'score': confidence,
                'class_id': class_id,
                'class_name': self.RELEVANT_CLASSES[class_id]
            }
            
            if class_id == self.PERSON_CLASS:
                detections['persons'].append(detection)
            else:
                detections['objects'].append(detection)
        
        return detections
    
    def detect_phones_near_persons(
        self, 
        persons: List[dict], 
        objects: List[dict],
        iou_threshold: float = 0.1
    ) -> List[Tuple[int, dict]]:
        """
        Find phones that are near/overlapping with person bboxes.
        
        Returns:
            List of (person_index, phone_detection) tuples
        """
        phone_associations = []
        
        phones = [obj for obj in objects if obj['class_name'] == 'phone']
        
        for phone in phones:
            phone_bbox = np.array(phone['bbox'])
            phone_center = np.array([
                (phone_bbox[0] + phone_bbox[2]) / 2,
                (phone_bbox[1] + phone_bbox[3]) / 2
            ])
            
            # Find nearest person
            min_dist = float('inf')
            nearest_person_idx = -1
            
            for i, person in enumerate(persons):
                person_bbox = np.array(person['bbox'])
                
                # Check if phone center is inside person bbox
                if (person_bbox[0] <= phone_center[0] <= person_bbox[2] and
                    person_bbox[1] <= phone_center[1] <= person_bbox[3]):
                    nearest_person_idx = i
                    break
                
                # Calculate distance to person bbox center
                person_center = np.array([
                    (person_bbox[0] + person_bbox[2]) / 2,
                    (person_bbox[1] + person_bbox[3]) / 2
                ])
                dist = np.linalg.norm(phone_center - person_center)
                
                if dist < min_dist:
                    min_dist = dist
                    nearest_person_idx = i
            
            if nearest_person_idx >= 0:
                phone_associations.append((nearest_person_idx, phone))
        
        return phone_associations


class FaceDetector:
    """InsightFace-based face detector and embedding extractor."""
    
    def __init__(self, det_threshold: float = 0.5, rec_threshold: float = 0.4):
        self.det_threshold = det_threshold
        self.rec_threshold = rec_threshold
        self.app = None
    
    def initialize(self):
        """Initialize the model."""
        self.app = get_face_app()
    
    def detect_faces(self, frame: np.ndarray) -> List[dict]:
        """
        Detect faces in frame.
        
        Args:
            frame: BGR image
        
        Returns:
            List of face detections with bbox and landmarks
        """
        if self.app is None:
            self.initialize()
        
        faces = self.app.get(frame)
        
        detections = []
        for face in faces:
            if face.det_score < self.det_threshold:
                continue
            
            detections.append({
                'bbox': face.bbox.tolist(),
                'score': float(face.det_score),
                'landmarks': face.kps.tolist() if face.kps is not None else None,
                'embedding': face.embedding.tolist() if face.embedding is not None else None,
                'age': int(face.age) if hasattr(face, 'age') and face.age else None,
                'gender': 'M' if hasattr(face, 'gender') and face.gender == 1 else 'F' if hasattr(face, 'gender') else None
            })
        
        return detections
    
    def extract_embedding(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract face embedding from frame (assumes single face).
        
        Args:
            frame: BGR image containing a face
        
        Returns:
            512-dimensional embedding vector or None
        """
        if self.app is None:
            self.initialize()
        
        faces = self.app.get(frame)
        
        if len(faces) == 0:
            return None
        
        # Return embedding of largest face
        largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        
        if largest_face.embedding is None:
            return None
        
        return largest_face.embedding
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1, embedding2: 512-dimensional vectors
        
        Returns:
            Similarity score between 0 and 1
        """
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)
        
        # Normalize embeddings
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1 = embedding1 / norm1
        embedding2 = embedding2 / norm2
        
        # Cosine similarity
        similarity = np.dot(embedding1, embedding2)
        
        # Convert to 0-1 range
        return (similarity + 1) / 2
    
    def match_embedding(
        self, 
        query_embedding: np.ndarray,
        known_embeddings: List[Dict],
        threshold: float = None
    ) -> Optional[Dict]:
        """
        Match a query embedding against known embeddings.
        
        Args:
            query_embedding: 512-dimensional vector
            known_embeddings: List of dicts with 'student_id' and 'embedding'
            threshold: Minimum similarity threshold
        
        Returns:
            Best match dict with 'student_id', 'similarity' or None
        """
        if threshold is None:
            threshold = self.rec_threshold
        
        if len(known_embeddings) == 0:
            return None
        
        best_match = None
        best_similarity = threshold
        
        for known in known_embeddings:
            similarity = self.compute_similarity(query_embedding, known['embedding'])
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    'student_id': known['student_id'],
                    'student_name': known.get('student_name'),
                    'similarity': similarity
                }
        
        return best_match


class FaceEnrollmentManager:
    """Manages face enrollment process with temporary storage."""
    
    def __init__(self, min_images: int = 10, max_images: int = 20):
        self.min_images = min_images
        self.max_images = max_images
        self.face_detector = FaceDetector()
        
        # Temporary storage for enrollment embeddings (studentId -> list of embeddings)
        self._enrollment_data: Dict[str, List[np.ndarray]] = {}
        self._enrollment_lock = threading.Lock()
    
    def start_enrollment(self, student_id: str):
        """Start enrollment for a student."""
        with self._enrollment_lock:
            self._enrollment_data[student_id] = []
    
    def capture_face(self, student_id: str, frame: np.ndarray) -> Dict:
        """
        Capture a face image for enrollment.
        
        Returns:
            Dict with 'success', 'face_detected', 'face_quality', etc.
        """
        if self.face_detector.app is None:
            self.face_detector.initialize()
        
        faces = self.face_detector.app.get(frame)
        
        if len(faces) == 0:
            return {
                'success': False,
                'face_detected': False,
                'error': 'No face detected'
            }
        
        if len(faces) > 1:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Multiple faces detected. Please ensure only one person is in frame.'
            }
        
        face = faces[0]
        
        # Check face quality
        bbox = face.bbox
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        
        if face_width < 100 or face_height < 100:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Face too small. Please move closer to the camera.',
                'face_quality': 'too_small'
            }
        
        if face.det_score < 0.7:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Face not clear. Please face the camera directly.',
                'face_quality': 'low_confidence'
            }
        
        # Store embedding
        with self._enrollment_lock:
            if student_id not in self._enrollment_data:
                self._enrollment_data[student_id] = []
            
            if len(self._enrollment_data[student_id]) >= self.max_images:
                return {
                    'success': False,
                    'face_detected': True,
                    'error': 'Maximum captures reached'
                }
            
            self._enrollment_data[student_id].append(face.embedding)
        
        return {
            'success': True,
            'face_detected': True,
            'face_quality': 'good',
            'det_score': float(face.det_score),
            'capture_count': len(self._enrollment_data.get(student_id, []))
        }
    
    def complete_enrollment(self, student_id: str) -> Dict:
        """
        Complete enrollment by averaging embeddings.
        
        Returns:
            Dict with 'success', 'embedding', 'quality' info
        """
        with self._enrollment_lock:
            if student_id not in self._enrollment_data:
                return {
                    'success': False,
                    'error': 'No enrollment data found'
                }
            
            embeddings = self._enrollment_data[student_id]
            
            if len(embeddings) < self.min_images:
                return {
                    'success': False,
                    'error': f'Minimum {self.min_images} images required, got {len(embeddings)}'
                }
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings)
            
            # Compute averaged embedding
            averaged_embedding = np.mean(embeddings_array, axis=0)
            
            # Normalize
            norm = np.linalg.norm(averaged_embedding)
            if norm > 0:
                averaged_embedding = averaged_embedding / norm
            
            # Compute consistency (standard deviation across embeddings)
            # Lower is better - means embeddings are more consistent
            consistency = np.mean(np.std(embeddings_array, axis=0))
            
            # Compute average confidence (similarity of each embedding to averaged)
            similarities = []
            for emb in embeddings:
                sim = np.dot(emb / np.linalg.norm(emb), averaged_embedding)
                similarities.append(sim)
            avg_confidence = np.mean(similarities)
            
            # Clean up temporary data
            del self._enrollment_data[student_id]
            
            return {
                'success': True,
                'embedding': averaged_embedding.tolist(),
                'quality': {
                    'averageConfidence': float(avg_confidence),
                    'imagesUsed': len(embeddings),
                    'consistency': float(consistency)
                },
                'modelInfo': {
                    'name': 'buffalo_l',
                    'version': 'insightface-0.7'
                }
            }
    
    def reset_enrollment(self, student_id: str):
        """Reset enrollment data for a student."""
        with self._enrollment_lock:
            if student_id in self._enrollment_data:
                del self._enrollment_data[student_id]
    
    def get_enrollment_status(self, student_id: str) -> Dict:
        """Get enrollment status for a student."""
        with self._enrollment_lock:
            if student_id not in self._enrollment_data:
                return {
                    'started': False,
                    'capture_count': 0
                }
            
            return {
                'started': True,
                'capture_count': len(self._enrollment_data[student_id]),
                'min_required': self.min_images,
                'max_allowed': self.max_images
            }
