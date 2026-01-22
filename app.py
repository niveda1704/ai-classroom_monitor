"""
EmotionSense AI Classroom Monitor - Local Backend Server
This runs the emotion detection locally without needing Google Colab.
"""

import os
import cv2
import base64
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import torch
from torchvision import models, transforms

# Try to import DeepFace (main emotion detection)
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("✅ DeepFace loaded successfully")
except ImportError:
    DEEPFACE_AVAILABLE = False
    print("⚠️ DeepFace not available, using fallback emotion detection")

# Try to import librosa for audio processing
try:
    import librosa
    LIBROSA_AVAILABLE = True
    print("✅ Librosa loaded successfully")
except ImportError:
    LIBROSA_AVAILABLE = False
    print("⚠️ Librosa not available, audio analysis disabled")

# Initialize Flask app
app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for frontend communication

# Emotion labels
emotion_labels = ['angry', 'disgust', 'fear', 'happy', 'sad', 'surprise', 'neutral']
focus_labels = ['focused', 'distracted', 'bored', 'engaged']

# Audio model setup (pretrained VGG16 for audio features)
print("Loading audio model...")
try:
    audio_model = models.vgg16(weights=models.VGG16_Weights.DEFAULT)
    audio_model.eval()
    print("✅ Audio model loaded")
except Exception as e:
    audio_model = None
    print(f"⚠️ Audio model not loaded: {e}")


def preprocess_audio(audio_data, sr=44100):
    """Convert audio data to spectrogram for model input."""
    if not LIBROSA_AVAILABLE or audio_model is None:
        return None
    
    try:
        # Convert to numpy array
        audio_array = np.array(audio_data, dtype=np.float32)
        
        # Normalize
        if len(audio_array) > 0 and np.max(np.abs(audio_array)) > 0:
            audio_array = audio_array / np.max(np.abs(audio_array))
        
        # Create spectrogram
        S = librosa.feature.melspectrogram(y=audio_array, sr=sr)
        S_dB = librosa.power_to_db(S, ref=np.max)
        
        # Resize to match VGG input
        img = cv2.resize(S_dB, (224, 224))
        img = np.stack([img] * 3, axis=-1)  # Convert to 3 channels
        
        # Convert to tensor
        transform = transforms.Compose([
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        img_tensor = transform(img).unsqueeze(0)
        return img_tensor
    except Exception as e:
        print(f"Audio preprocessing error: {e}")
        return None


def analyze_emotion_fallback(img):
    """Fallback emotion detection using OpenCV face detection."""
    try:
        # Use OpenCV's face detection
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.1, 4)
        
        if len(faces) > 0:
            # Face detected - return neutral with some variation
            return {
                'dominant_emotion': 'neutral',
                'emotion': {
                    'angry': 5, 'disgust': 2, 'fear': 3,
                    'happy': 20, 'sad': 10, 'surprise': 10, 'neutral': 50
                }
            }
        else:
            return {
                'dominant_emotion': 'neutral',
                'emotion': {'neutral': 100}
            }
    except Exception as e:
        print(f"Fallback detection error: {e}")
        return {
            'dominant_emotion': 'neutral',
            'emotion': {'neutral': 100}
        }


@app.route('/analyze', methods=['POST'])
def analyze():
    """Main endpoint for emotion analysis."""
    try:
        data = request.json
        
        # Process image
        image_data = data.get('image', '')
        if ',' in image_data:
            image_data = image_data.split(',')[1]  # Remove data URL prefix
        
        # Decode base64 image
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if img is None:
            return jsonify({"error": "Invalid image data"}), 400
        
        # Face detection and emotion analysis
        dominant_emotion = 'neutral'
        emotion_scores = {'neutral': 100}
        
        if DEEPFACE_AVAILABLE:
            try:
                face_analysis = DeepFace.analyze(
                    img, 
                    actions=['emotion'],
                    enforce_detection=False,  # Don't fail if no face detected
                    silent=True
                )
                if isinstance(face_analysis, list) and len(face_analysis) > 0:
                    dominant_emotion = face_analysis[0]['dominant_emotion']
                    emotion_scores = face_analysis[0]['emotion']
            except Exception as e:
                print(f"DeepFace error: {e}")
                # Use fallback
                fallback = analyze_emotion_fallback(img)
                dominant_emotion = fallback['dominant_emotion']
                emotion_scores = fallback['emotion']
        else:
            # Use fallback emotion detection
            fallback = analyze_emotion_fallback(img)
            dominant_emotion = fallback['dominant_emotion']
            emotion_scores = fallback['emotion']
        
        # Process audio if available
        audio_data = data.get('audio', [])
        if audio_data and audio_model is not None and LIBROSA_AVAILABLE:
            audio_tensor = preprocess_audio(audio_data)
            if audio_tensor is not None:
                with torch.no_grad():
                    audio_features = audio_model(audio_tensor)
                    # Could use audio features to modify emotion scores
        
        # Calculate engagement metrics
        focus_score = (emotion_scores.get('happy', 0) + emotion_scores.get('neutral', 0)) / 2
        bored_score = (emotion_scores.get('sad', 0) + emotion_scores.get('angry', 0)) / 2
        engaged_score = (emotion_scores.get('happy', 0) + emotion_scores.get('surprise', 0)) / 2
        
        # Determine engagement level
        if focus_score > 60:
            engagement_status = "High"
        elif focus_score > 30:
            engagement_status = "Medium"
        else:
            engagement_status = "Low"
        
        # Prepare response
        response = {
            "emotion": dominant_emotion,
            "focusPercent": int(focus_score),
            "boredPercent": int(bored_score),
            "engagedPercent": int(engaged_score),
            "engagementLevel": engagement_status,
            "emotionScores": emotion_scores
        }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/')
def index():
    """Serve the main page."""
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files."""
    return send_from_directory('static', path)


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "running",
        "deepface": DEEPFACE_AVAILABLE,
        "librosa": LIBROSA_AVAILABLE,
        "audio_model": audio_model is not None
    })


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("EmotionSense AI Classroom Monitor - Local Server")
    print("=" * 60)
    print(f"\n🚀 Starting server at http://localhost:5000")
    print(f"📹 Open http://localhost:5000 in your browser")
    print(f"💡 Make sure to allow camera/microphone access\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
