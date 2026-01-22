"""
AI Service Configuration
"""

import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    
    # MongoDB
    mongodb_uri: str = "mongodb://localhost:27017/classroom_analytics"
    
    # Model Settings
    yolo_model: str = "yolov8n.pt"
    yolo_conf_threshold: float = 0.5
    face_det_threshold: float = 0.5
    face_rec_threshold: float = 0.4
    
    # Processing
    target_fps: int = 8
    max_frame_width: int = 1280
    max_frame_height: int = 720
    
    # Enrollment
    min_enrollment_images: int = 10
    max_enrollment_images: int = 20
    embedding_dimension: int = 512
    
    # Snippet Recording
    snippet_duration_seconds: int = 10
    snippet_output_dir: str = "./snippets"
    snippet_format: str = "mp4"
    
    # Backend Communication
    backend_url: str = "http://localhost:3001"
    backend_ws_url: str = "ws://localhost:3001/ws"
    
    # Paths
    base_dir: Path = Path(__file__).parent.parent
    models_dir: Path = base_dir / "models"
    temp_dir: Path = base_dir / "temp"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

# Ensure directories exist
settings.models_dir.mkdir(parents=True, exist_ok=True)
settings.temp_dir.mkdir(parents=True, exist_ok=True)
Path(settings.snippet_output_dir).mkdir(parents=True, exist_ok=True)
