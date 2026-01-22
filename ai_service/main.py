"""
AI Classroom Monitoring Service
FastAPI-based microservice for real-time classroom analytics
"""

import os
import sys
import asyncio
import base64
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger
from pymongo import MongoClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from pipeline import MonitoringPipeline
from models import FaceEnrollmentManager


# ============ Pydantic Models ============

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    models_loaded: bool
    gpu_available: bool


class EnrollmentCaptureRequest(BaseModel):
    studentId: str
    imageData: str  # Base64 encoded image
    captureIndex: int = 0


class EnrollmentCompleteRequest(BaseModel):
    studentId: str


class SessionStartRequest(BaseModel):
    sessionId: str
    camera: Dict
    expectedDuration: int


class SessionStopRequest(BaseModel):
    sessionId: str


class FrameProcessRequest(BaseModel):
    sessionId: str
    imageData: str  # Base64 encoded frame
    timestamp: Optional[str] = None


class EmbeddingMatchRequest(BaseModel):
    embedding: List[float]
    threshold: float = 0.4


# ============ Global State ============

class AppState:
    def __init__(self):
        self.pipeline: Optional[MonitoringPipeline] = None
        self.enrollment_manager: Optional[FaceEnrollmentManager] = None
        self.db_client: Optional[MongoClient] = None
        self.db = None
        self.models_initialized = False
        self.active_sessions: Dict[str, dict] = {}


state = AppState()


# ============ Lifespan Events ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    logger.info("Starting AI Service...")
    
    # Try MongoDB connection (optional - works without it)
    try:
        state.db_client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=2000)
        state.db_client.server_info()  # Test connection
        state.db = state.db_client.get_database()
        logger.info("MongoDB connected")
    except Exception as e:
        logger.warning(f"MongoDB not available, using in-memory storage: {e}")
        state.db_client = None
        state.db = None
    
    # Initialize models in background
    asyncio.create_task(initialize_models())
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI Service...")
    
    # Stop active sessions
    if state.pipeline:
        for session_id in list(state.active_sessions.keys()):
            try:
                state.pipeline.stop_session()
            except:
                pass
    
    # Close MongoDB connection
    if state.db_client:
        state.db_client.close()
    
    logger.info("AI Service shutdown complete")


async def initialize_models():
    """Initialize AI models in background."""
    try:
        logger.info("Initializing AI models...")
        
        # Initialize enrollment manager
        state.enrollment_manager = FaceEnrollmentManager(
            min_images=settings.min_enrollment_images,
            max_images=settings.max_enrollment_images
        )
        
        # Initialize pipeline
        state.pipeline = MonitoringPipeline(
            target_fps=settings.target_fps
        )
        state.pipeline.initialize()
        
        state.models_initialized = True
        logger.info("AI models initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize models: {e}")
        state.models_initialized = False


# ============ FastAPI App ============

app = FastAPI(
    title="AI Classroom Monitoring Service",
    description="Real-time classroom analytics with computer vision",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Utility Functions ============

def decode_base64_image(image_data: str) -> np.ndarray:
    """Decode base64 image data to numpy array."""
    # Remove data URL prefix if present
    if ',' in image_data:
        image_data = image_data.split(',')[1]
    
    # Decode base64
    image_bytes = base64.b64decode(image_data)
    
    # Convert to numpy array
    nparr = np.frombuffer(image_bytes, np.uint8)
    
    # Decode image
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if image is None:
        raise ValueError("Failed to decode image")
    
    return image


def get_known_embeddings() -> List[Dict]:
    """Fetch known embeddings from MongoDB."""
    if state.db is None:
        return []
    
    try:
        embeddings_collection = state.db['embeddings']
        students_collection = state.db['students']
        
        embeddings = []
        for emb_doc in embeddings_collection.find():
            student = students_collection.find_one({'_id': emb_doc['studentId']})
            if student:
                embeddings.append({
                    'student_id': str(student['_id']),
                    'student_name': student.get('name'),
                    'embedding': emb_doc['embedding']
                })
        
        return embeddings
    except Exception as e:
        logger.error(f"Failed to fetch embeddings: {e}")
        return []


# ============ Health Endpoints ============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import torch
    
    return HealthResponse(
        status="healthy" if state.models_initialized else "initializing",
        timestamp=datetime.now().isoformat(),
        models_loaded=state.models_initialized,
        gpu_available=torch.cuda.is_available()
    )


@app.get("/api/models/status")
async def get_model_status():
    """Get status of loaded models."""
    import torch
    
    return {
        "initialized": state.models_initialized,
        "gpu_available": torch.cuda.is_available(),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "active_sessions": len(state.active_sessions)
    }


# ============ Enrollment Endpoints ============

@app.post("/api/enrollment/capture")
async def enrollment_capture(request: EnrollmentCaptureRequest):
    """Capture a face image for student enrollment."""
    if not state.models_initialized:
        raise HTTPException(status_code=503, detail="Models not initialized")
    
    try:
        # Decode image
        image = decode_base64_image(request.imageData)
        
        # Resize if too large
        max_dim = max(image.shape[:2])
        if max_dim > 1280:
            scale = 1280 / max_dim
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        # Process capture
        result = state.enrollment_manager.capture_face(request.studentId, image)
        
        return {
            "success": result['success'],
            "faceDetected": result.get('face_detected', False),
            "faceQuality": result.get('face_quality'),
            "error": result.get('error'),
            "captureCount": result.get('capture_count', 0)
        }
        
    except Exception as e:
        logger.error(f"Enrollment capture error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/enrollment/complete")
async def enrollment_complete(request: EnrollmentCompleteRequest):
    """Complete enrollment and compute averaged embedding."""
    if not state.models_initialized:
        raise HTTPException(status_code=503, detail="Models not initialized")
    
    try:
        result = state.enrollment_manager.complete_enrollment(request.studentId)
        
        return {
            "success": result['success'],
            "embedding": result.get('embedding'),
            "quality": result.get('quality'),
            "modelInfo": result.get('modelInfo'),
            "error": result.get('error')
        }
        
    except Exception as e:
        logger.error(f"Enrollment complete error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/enrollment/reset")
async def enrollment_reset(request: EnrollmentCompleteRequest):
    """Reset enrollment for a student."""
    if state.enrollment_manager:
        state.enrollment_manager.reset_enrollment(request.studentId)
    
    return {"success": True, "message": "Enrollment reset"}


@app.get("/api/enrollment/status/{student_id}")
async def enrollment_status(student_id: str):
    """Get enrollment status for a student."""
    if not state.enrollment_manager:
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return state.enrollment_manager.get_enrollment_status(student_id)


# ============ Session Endpoints ============

@app.post("/api/session/start")
async def session_start(request: SessionStartRequest):
    """Start a monitoring session."""
    if not state.models_initialized:
        raise HTTPException(status_code=503, detail="Models not initialized")
    
    if request.sessionId in state.active_sessions:
        raise HTTPException(status_code=400, detail="Session already running")
    
    try:
        # Fetch known embeddings for recognition
        known_embeddings = get_known_embeddings()
        state.pipeline.update_known_embeddings(known_embeddings)
        
        # Start session
        state.pipeline.start_session(request.sessionId)
        
        state.active_sessions[request.sessionId] = {
            'started_at': datetime.now().isoformat(),
            'camera': request.camera,
            'expected_duration': request.expectedDuration
        }
        
        return {
            "success": True,
            "sessionId": request.sessionId,
            "message": "Session started",
            "knownStudents": len(known_embeddings)
        }
        
    except Exception as e:
        logger.error(f"Session start error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/stop")
async def session_stop(request: SessionStopRequest):
    """Stop a monitoring session."""
    if request.sessionId not in state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        analytics = state.pipeline.stop_session()
        del state.active_sessions[request.sessionId]
        
        return {
            "success": True,
            "sessionId": request.sessionId,
            "analytics": analytics
        }
        
    except Exception as e:
        logger.error(f"Session stop error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/session/pause")
async def session_pause(request: SessionStopRequest):
    """Pause a monitoring session."""
    if request.sessionId not in state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state.pipeline.is_running = False
    return {"success": True, "message": "Session paused"}


@app.post("/api/session/resume")
async def session_resume(request: SessionStopRequest):
    """Resume a paused session."""
    if request.sessionId not in state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    state.pipeline.is_running = True
    return {"success": True, "message": "Session resumed"}


@app.post("/api/session/complete")
async def session_complete(request: SessionStopRequest):
    """Complete a session and get final analytics."""
    return await session_stop(request)


@app.get("/api/session/{session_id}/status")
async def session_status(session_id: str):
    """Get current session status and metrics."""
    if session_id not in state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    metrics = state.pipeline.get_current_metrics() if state.pipeline else {}
    
    return {
        "sessionId": session_id,
        "info": state.active_sessions[session_id],
        "metrics": metrics
    }


# ============ Frame Processing Endpoints ============

@app.post("/api/process-frame")
async def process_frame_simple(request: FrameProcessRequest):
    """
    Process a single frame - simplified endpoint for frontend.
    Doesn't require session to be started in AI service.
    """
    if not state.models_initialized:
        raise HTTPException(status_code=503, detail="Models not initialized")
    
    try:
        # Decode image
        image = decode_base64_image(request.imageData)
        
        # Resize if needed
        h, w = image.shape[:2]
        if w > settings.max_frame_width or h > settings.max_frame_height:
            scale = min(
                settings.max_frame_width / w,
                settings.max_frame_height / h
            )
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        # Process frame through pipeline
        result = state.pipeline.process_frame_sync(image)
        
        # Return metrics, detected students, and events
        return {
            "success": True,
            "metrics": {
                "studentCount": result.get('person_count', 0),
                "avgAttention": result.get('average_attention', 0) * 100,
                "phoneUsage": result.get('phone_count', 0),
                "distractions": result.get('distraction_count', 0)
            },
            "students": result.get('students', []),
            "events": result.get('events', [])
        }
        
    except Exception as e:
        logger.error(f"Frame processing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/frame/process")
async def process_frame(request: FrameProcessRequest):
    """Process a single frame."""
    if not state.models_initialized:
        raise HTTPException(status_code=503, detail="Models not initialized")
    
    if request.sessionId not in state.active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    try:
        # Decode image
        image = decode_base64_image(request.imageData)
        
        # Resize if needed
        h, w = image.shape[:2]
        if w > settings.max_frame_width or h > settings.max_frame_height:
            scale = min(
                settings.max_frame_width / w,
                settings.max_frame_height / h
            )
            image = cv2.resize(image, None, fx=scale, fy=scale)
        
        # Process frame
        result = await state.pipeline.process_frame(image)
        
        return result
        
    except Exception as e:
        logger.error(f"Frame processing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============ Recognition Endpoints ============

@app.post("/api/recognition/match")
async def match_embedding(request: EmbeddingMatchRequest):
    """Match an embedding against known students."""
    if not state.models_initialized:
        raise HTTPException(status_code=503, detail="Models not initialized")
    
    try:
        known_embeddings = get_known_embeddings()
        
        if len(known_embeddings) == 0:
            return {"success": True, "match": None, "message": "No known embeddings"}
        
        from models import FaceDetector
        detector = FaceDetector()
        
        match = detector.match_embedding(
            np.array(request.embedding),
            known_embeddings,
            threshold=request.threshold
        )
        
        return {
            "success": True,
            "match": match
        }
        
    except Exception as e:
        logger.error(f"Embedding match error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============ Camera Endpoints ============

@app.get("/api/cameras")
async def get_cameras():
    """Get available camera devices."""
    cameras = []
    
    # Check first 5 camera indices
    for i in range(5):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append({
                "index": i,
                "label": f"Camera {i}",
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            })
            cap.release()
    
    return {"cameras": cameras}


# ============ WebSocket Endpoint ============

@app.websocket("/ws/stream/{session_id}")
async def websocket_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time frame streaming."""
    await websocket.accept()
    
    if session_id not in state.active_sessions:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    logger.info(f"WebSocket connected for session: {session_id}")
    
    try:
        while True:
            # Receive frame data
            data = await websocket.receive_text()
            
            if not state.pipeline or not state.pipeline.is_running:
                await websocket.send_json({"error": "Session not active"})
                continue
            
            try:
                # Decode and process frame
                image = decode_base64_image(data)
                
                # Resize if needed
                h, w = image.shape[:2]
                if w > settings.max_frame_width:
                    scale = settings.max_frame_width / w
                    image = cv2.resize(image, None, fx=scale, fy=scale)
                
                # Process frame
                result = await state.pipeline.process_frame(image)
                
                # Send result back
                await websocket.send_json(result)
                
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info(f"WebSocket connection closed for session: {session_id}")


# ============ Main Entry Point ============

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
