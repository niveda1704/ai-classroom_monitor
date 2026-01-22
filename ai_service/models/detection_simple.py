"""
Simplified Detection Models Module
Uses MediaPipe Tasks for face detection (no InsightFace dependency)
"""

import numpy as np
import cv2
from typing import List, Dict, Tuple, Optional
import threading
import os
from loguru import logger

# Lazy imports
_yolo_model = None
_face_detector = None
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


def get_face_detection():
    """Get or initialize face detection using OpenCV's DNN or Haar cascades."""
    global _face_detector
    
    if _face_detector is None:
        with _models_lock:
            if _face_detector is None:
                try:
                    # Use OpenCV's built-in face detector (Haar cascade)
                    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    _face_detector = cv2.CascadeClassifier(cascade_path)
                    logger.info("OpenCV Face Detection loaded successfully")
                except Exception as e:
                    logger.error(f"Failed to load face detector: {e}")
                    raise
    
    return _face_detector


class PersonDetector:
    """YOLOv8-based person and object detector."""
    
    PERSON_CLASS = 0
    PHONE_CLASS = 67
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
        """Detect persons and relevant objects in frame."""
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
                'bbox': bbox.tolist(),
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
        """Find phones that are near/overlapping with person bboxes."""
        phone_associations = []
        
        phones = [obj for obj in objects if obj['class_name'] == 'phone']
        
        for phone in phones:
            phone_bbox = np.array(phone['bbox'])
            phone_center = np.array([
                (phone_bbox[0] + phone_bbox[2]) / 2,
                (phone_bbox[1] + phone_bbox[3]) / 2
            ])
            
            min_dist = float('inf')
            nearest_person_idx = -1
            
            for i, person in enumerate(persons):
                person_bbox = np.array(person['bbox'])
                
                if (person_bbox[0] <= phone_center[0] <= person_bbox[2] and
                    person_bbox[1] <= phone_center[1] <= person_bbox[3]):
                    nearest_person_idx = i
                    break
                
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
    """OpenCV-based face detector with simple embedding generation."""
    
    def __init__(self, det_threshold: float = 0.5, rec_threshold: float = 0.6):
        self.det_threshold = det_threshold
        self.rec_threshold = rec_threshold
        self.face_cascade = None
    
    def initialize(self):
        """Initialize the models."""
        self.face_cascade = get_face_detection()
    
    def detect_faces(self, frame: np.ndarray) -> List[dict]:
        """Detect faces in frame using OpenCV."""
        if self.face_cascade is None:
            self.initialize()
        
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        
        # Detect faces
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60)
        )
        
        detections = []
        for (x, y, fw, fh) in faces:
            x1, y1, x2, y2 = x, y, x + fw, y + fh
            
            # Get face ROI for embedding
            face_roi = frame[y1:y2, x1:x2]
            embedding = self._generate_simple_embedding(face_roi) if face_roi.size > 0 else None
            
            detections.append({
                'bbox': [int(x1), int(y1), int(x2), int(y2)],
                'score': 0.9,  # Haar cascade doesn't provide confidence
                'landmarks': None,
                'embedding': embedding,
                'age': None,
                'gender': None
            })
        
        return detections
    
    def _generate_simple_embedding(self, face_roi: np.ndarray, size: int = 512) -> Optional[List[float]]:
        """
        Generate a simple embedding from face ROI using image features.
        Note: This is a simplified version - not as accurate as InsightFace.
        """
        try:
            if face_roi.size == 0:
                return None
            
            # Resize to standard size
            face_resized = cv2.resize(face_roi, (64, 64))
            
            # Convert to grayscale
            gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
            
            # Apply histogram equalization
            gray = cv2.equalizeHist(gray)
            
            # Compute LBP-like features (simplified)
            features = []
            
            # Flatten and normalize
            flat = gray.flatten().astype(np.float32)
            flat = flat / 255.0
            
            # Use DCT features
            dct = cv2.dct(gray.astype(np.float32))
            dct_features = dct[:32, :16].flatten()
            
            # Combine features
            embedding = np.zeros(size, dtype=np.float32)
            embedding[:len(flat)] = flat[:min(len(flat), size)]
            
            # Add DCT features
            dct_start = min(len(flat), size)
            dct_end = min(dct_start + len(dct_features), size)
            embedding[dct_start:dct_end] = dct_features[:dct_end - dct_start]
            
            # Normalize
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def extract_embedding(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Extract face embedding from frame."""
        detections = self.detect_faces(frame)
        
        if len(detections) == 0:
            return None
        
        # Return embedding of largest face
        largest = max(detections, key=lambda d: (d['bbox'][2] - d['bbox'][0]) * (d['bbox'][3] - d['bbox'][1]))
        
        if largest['embedding'] is None:
            return None
        
        return np.array(largest['embedding'])
    
    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        embedding1 = np.array(embedding1)
        embedding2 = np.array(embedding2)
        
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        embedding1 = embedding1 / norm1
        embedding2 = embedding2 / norm2
        
        similarity = np.dot(embedding1, embedding2)
        return (similarity + 1) / 2
    
    def match_embedding(
        self, 
        query_embedding: np.ndarray,
        known_embeddings: List[Dict],
        threshold: float = None
    ) -> Optional[Dict]:
        """Match a query embedding against known embeddings."""
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
    """Manages face enrollment using OpenCV-based detection."""
    
    def __init__(self, min_images: int = 10, max_images: int = 20):
        self.min_images = min_images
        self.max_images = max_images
        self.face_detector = FaceDetector()
        
        self._enrollment_data: Dict[str, List[np.ndarray]] = {}
        self._enrollment_lock = threading.Lock()
    
    def start_enrollment(self, student_id: str):
        """Start enrollment for a student."""
        with self._enrollment_lock:
            self._enrollment_data[student_id] = []
    
    def capture_face(self, student_id: str, frame: np.ndarray) -> Dict:
        """Capture a face image for enrollment."""
        if self.face_detector.face_cascade is None:
            self.face_detector.initialize()
        
        detections = self.face_detector.detect_faces(frame)
        
        if len(detections) == 0:
            return {
                'success': False,
                'face_detected': False,
                'error': 'No face detected'
            }
        
        if len(detections) > 1:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Multiple faces detected. Please ensure only one person is in frame.'
            }
        
        face = detections[0]
        
        # Check face quality
        bbox = face['bbox']
        face_width = bbox[2] - bbox[0]
        face_height = bbox[3] - bbox[1]
        
        if face_width < 80 or face_height < 80:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Face too small. Please move closer to the camera.',
                'face_quality': 'too_small'
            }
        
        if face['score'] < 0.7:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Face not clear. Please face the camera directly.',
                'face_quality': 'low_confidence'
            }
        
        if face['embedding'] is None:
            return {
                'success': False,
                'face_detected': True,
                'error': 'Could not extract face features',
                'face_quality': 'no_embedding'
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
            
            self._enrollment_data[student_id].append(np.array(face['embedding']))
        
        return {
            'success': True,
            'face_detected': True,
            'face_quality': 'good',
            'det_score': float(face['score']),
            'capture_count': len(self._enrollment_data.get(student_id, []))
        }
    
    def complete_enrollment(self, student_id: str) -> Dict:
        """Complete enrollment by averaging embeddings."""
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
            
            embeddings_array = np.array(embeddings)
            averaged_embedding = np.mean(embeddings_array, axis=0)
            
            norm = np.linalg.norm(averaged_embedding)
            if norm > 0:
                averaged_embedding = averaged_embedding / norm
            
            consistency = np.mean(np.std(embeddings_array, axis=0))
            
            similarities = []
            for emb in embeddings:
                emb_norm = np.linalg.norm(emb)
                if emb_norm > 0:
                    sim = np.dot(emb / emb_norm, averaged_embedding)
                    similarities.append(sim)
            avg_confidence = np.mean(similarities) if similarities else 0.0
            
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
                    'name': 'mediapipe_simple',
                    'version': '1.0'
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


# Compatibility aliases
def get_face_app():
    """Compatibility function - returns None since we don't use InsightFace."""
    return None
