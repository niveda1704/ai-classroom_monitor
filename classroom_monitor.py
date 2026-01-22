"""
AI Classroom Monitoring System
Detects student engagement, attention, and emotions in real-time.

Uses only OpenCV - no external ML dependencies needed!
"""

import cv2
import numpy as np
import base64
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from collections import deque
import time
import os

# Initialize Flask
app = Flask(__name__, static_folder='static')
CORS(app)

# Load OpenCV's pre-trained detectors
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
eye_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

print("✅ OpenCV Face/Eye/Smile detectors loaded")

# Student tracking data
class StudentTracker:
    def __init__(self):
        self.attention_history = deque(maxlen=30)
        self.emotion_history = deque(maxlen=30)
        self.engagement_history = deque(maxlen=30)
        self.drowsiness_history = deque(maxlen=30)
        
    def add_reading(self, attention, emotion, engagement, drowsiness):
        self.attention_history.append(attention)
        self.emotion_history.append(emotion)
        self.engagement_history.append(engagement)
        self.drowsiness_history.append(drowsiness)
    
    def get_averages(self):
        return {
            'attention': np.mean(self.attention_history) if self.attention_history else 0,
            'engagement': np.mean(self.engagement_history) if self.engagement_history else 0,
            'drowsiness': np.mean(self.drowsiness_history) if self.drowsiness_history else 0
        }

tracker = StudentTracker()


def analyze_face(face_roi_gray, face_roi_color):
    """
    Analyze a single face for attention, drowsiness, and emotion.
    """
    h, w = face_roi_gray.shape
    
    # Detect eyes
    eyes = eye_cascade.detectMultiScale(face_roi_gray, 1.1, 5, minSize=(20, 20))
    
    # Detect smile
    smiles = smile_cascade.detectMultiScale(face_roi_gray, 1.8, 20, minSize=(25, 25))
    
    # Calculate attention based on face position and eyes
    attention = 70  # Base attention
    
    # If eyes detected, student is likely paying attention
    if len(eyes) >= 2:
        attention = 85
    elif len(eyes) == 1:
        attention = 60  # Might be looking sideways
    else:
        attention = 40  # Eyes not detected - looking away or closed
    
    # Calculate drowsiness based on eye detection
    if len(eyes) == 0:
        drowsiness = 70  # Eyes closed or looking away
    elif len(eyes) == 1:
        drowsiness = 40
    else:
        # Check eye openness by analyzing the eye regions
        drowsiness = 20
        for (ex, ey, ew, eh) in eyes:
            eye_aspect_ratio = eh / ew if ew > 0 else 0
            if eye_aspect_ratio < 0.3:  # Eyes more closed
                drowsiness += 20
    
    drowsiness = min(100, max(0, drowsiness))
    
    # Detect emotion based on smile
    if len(smiles) > 0:
        emotion = 'happy'
        engagement = 80
    else:
        emotion = 'neutral'
        engagement = 50
    
    # Adjust engagement based on attention
    engagement = (engagement + attention) / 2
    
    return {
        'attention': round(attention, 1),
        'drowsiness': round(drowsiness, 1),
        'emotion': emotion,
        'engagement': round(engagement, 1),
        'eyes_detected': len(eyes),
        'smiling': len(smiles) > 0
    }


def analyze_classroom(image):
    """
    Main analysis function - detects faces and analyzes engagement.
    """
    results = {
        'students_detected': 0,
        'faces': [],
        'class_attention': 0,
        'class_engagement': 0,
        'class_drowsiness': 0,
        'dominant_emotion': 'neutral',
        'alerts': []
    }
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Detect faces
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60)
    )
    
    results['students_detected'] = len(faces)
    
    if len(faces) == 0:
        return results
    
    total_attention = 0
    total_engagement = 0
    total_drowsiness = 0
    emotions = []
    
    for idx, (x, y, w, h) in enumerate(faces):
        # Extract face region
        face_roi_gray = gray[y:y+h, x:x+w]
        face_roi_color = image[y:y+h, x:x+w]
        
        # Analyze this face
        analysis = analyze_face(face_roi_gray, face_roi_color)
        
        total_attention += analysis['attention']
        total_engagement += analysis['engagement']
        total_drowsiness += analysis['drowsiness']
        emotions.append(analysis['emotion'])
        
        # Store face data
        results['faces'].append({
            'id': idx + 1,
            'attention': analysis['attention'],
            'drowsiness': analysis['drowsiness'],
            'emotion': analysis['emotion'],
            'engagement': analysis['engagement'],
            'bbox': {'x': int(x), 'y': int(y), 'w': int(w), 'h': int(h)}
        })
        
        # Generate alerts
        if analysis['attention'] < 40:
            results['alerts'].append(f"Student {idx+1}: Low attention ({analysis['attention']:.0f}%)")
        if analysis['drowsiness'] > 60:
            results['alerts'].append(f"Student {idx+1}: Appears drowsy ({analysis['drowsiness']:.0f}%)")
    
    # Calculate class averages
    num_faces = len(faces)
    results['class_attention'] = round(total_attention / num_faces, 1)
    results['class_engagement'] = round(total_engagement / num_faces, 1)
    results['class_drowsiness'] = round(total_drowsiness / num_faces, 1)
    
    # Determine dominant emotion
    if emotions:
        results['dominant_emotion'] = max(set(emotions), key=emotions.count)
    
    # Update tracker
    tracker.add_reading(
        results['class_attention'],
        results['dominant_emotion'],
        results['class_engagement'],
        results['class_drowsiness']
    )
    
    return results


@app.route('/analyze', methods=['POST'])
def analyze():
    """API endpoint for frame analysis."""
    try:
        data = request.json
        
        # Decode image
        image_data = data.get('image', '')
        if ',' in image_data:
            image_data = image_data.split(',')[1]
        
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': 'Invalid image'}), 400
        
        # Analyze
        results = analyze_classroom(image)
        
        # Add historical averages
        averages = tracker.get_averages()
        results['avg_attention'] = round(averages['attention'], 1)
        results['avg_engagement'] = round(averages['engagement'], 1)
        results['avg_drowsiness'] = round(averages['drowsiness'], 1)
        
        return jsonify(results)
        
    except Exception as e:
        print(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/health')
def health():
    return jsonify({
        'status': 'running',
        'face_detection': True,
        'eye_detection': True,
        'smile_detection': True
    })


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("🎓 AI Classroom Monitoring System")
    print("=" * 60)
    print("\n📊 Features:")
    print("   • Face Detection (multiple students)")
    print("   • Attention Tracking (eye detection)")
    print("   • Drowsiness Detection")
    print("   • Smile/Emotion Detection")
    print("\n🚀 Server starting at http://localhost:5000")
    print("📹 Open browser and allow camera access\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
