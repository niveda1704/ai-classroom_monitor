"""
Student Enrollment Window - Face capture for recognition
"""

import cv2
import numpy as np
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_manager import data_manager, EMBEDDINGS_DIR


class CameraThread(QThread):
    """Thread for camera capture."""
    frame_ready = pyqtSignal(np.ndarray)
    
    def __init__(self):
        super().__init__()
        self.running = False
        self.cap = None
    
    def run(self):
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                self.frame_ready.emit(frame)
            self.msleep(33)  # ~30 FPS
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()


class EnrollmentWindow(QMainWindow):
    """Window for student face enrollment."""
    
    closed = pyqtSignal()
    
    def __init__(self, student_id: str):
        super().__init__()
        self.student_id = student_id
        self.student = data_manager.get_student(student_id)
        
        if not self.student:
            QMessageBox.critical(self, "Error", "Student not found!")
            self.close()
            return
        
        self.setWindowTitle(f"Enroll: {self.student.name}")
        self.setFixedSize(800, 600)
        self.setStyleSheet("background-color: #111827;")
        
        # Enrollment state
        self.captured_embeddings = []
        self.required_captures = 15
        self.current_frame = None
        self.face_detector = None
        
        self.setup_ui()
        self.init_models()
        
        # Camera thread
        self.camera_thread = CameraThread()
        self.camera_thread.frame_ready.connect(self.process_frame)
    
    def setup_ui(self):
        """Setup the enrollment UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # Header
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9ca3af;
                border: none;
                font-size: 14px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.close)
        header_layout.addWidget(back_btn)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Student info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(20, 16, 20, 16)
        
        avatar = QLabel(self.student.name[0].upper())
        avatar.setFixedSize(48, 48)
        avatar.setStyleSheet("""
            QLabel {
                background-color: #4f46e5;
                color: #ffffff;
                border-radius: 24px;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_layout.addWidget(avatar)
        
        name_layout = QVBoxLayout()
        name_label = QLabel(self.student.name)
        name_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        id_label = QLabel(f"ID: {self.student.student_id}")
        id_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        name_layout.addWidget(name_label)
        name_layout.addWidget(id_label)
        info_layout.addLayout(name_layout)
        
        info_layout.addStretch()
        
        # Status
        status_text = "Enrolled ✓" if self.student.enrollment_status == "enrolled" else "Not Enrolled"
        status_color = "#22c55e" if self.student.enrollment_status == "enrolled" else "#ef4444"
        self.status_label = QLabel(status_text)
        self.status_label.setStyleSheet(f"color: {status_color}; font-size: 14px; font-weight: 500;")
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_frame)
        
        # Main content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(24)
        
        # Camera view
        camera_frame = QFrame()
        camera_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        camera_layout = QVBoxLayout(camera_frame)
        camera_layout.setContentsMargins(16, 16, 16, 16)
        
        self.video_label = QLabel("Camera Preview")
        self.video_label.setFixedSize(480, 360)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #374151;
                border-radius: 8px;
                color: #6b7280;
                font-size: 14px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        camera_layout.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        content_layout.addWidget(camera_frame, stretch=2)
        
        # Controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(20, 20, 20, 20)
        controls_layout.setSpacing(16)
        
        # Instructions
        instructions_label = QLabel("Face Enrollment")
        instructions_label.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        controls_layout.addWidget(instructions_label)
        
        self.message_label = QLabel("Click 'Start Camera' to begin enrollment.\nCapture 15 photos from different angles.")
        self.message_label.setStyleSheet("color: #9ca3af; font-size: 13px;")
        self.message_label.setWordWrap(True)
        controls_layout.addWidget(self.message_label)
        
        # Progress
        progress_label = QLabel("Progress")
        progress_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        controls_layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, self.required_captures)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: #374151;
                border-radius: 6px;
                height: 12px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4f46e5;
                border-radius: 6px;
            }
        """)
        controls_layout.addWidget(self.progress_bar)
        
        self.progress_text = QLabel("0 / 15 captures")
        self.progress_text.setStyleSheet("color: #6b7280; font-size: 12px;")
        controls_layout.addWidget(self.progress_text)
        
        controls_layout.addStretch()
        
        # Buttons
        self.start_btn = QPushButton("📷  Start Camera")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle_camera)
        controls_layout.addWidget(self.start_btn)
        
        self.capture_btn = QPushButton("📸  Capture")
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
            QPushButton:disabled {
                background-color: #374151;
                color: #6b7280;
            }
        """)
        self.capture_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.capture_btn.clicked.connect(self.capture_face)
        self.capture_btn.setEnabled(False)
        controls_layout.addWidget(self.capture_btn)
        
        self.reset_btn = QPushButton("🔄  Reset")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 14px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_enrollment)
        controls_layout.addWidget(self.reset_btn)
        
        content_layout.addWidget(controls_frame, stretch=1)
        
        layout.addLayout(content_layout)
    
    def init_models(self):
        """Initialize face detection model."""
        try:
            from ai_service.models.detection import get_face_app
            self.face_detector = get_face_app()
            self.message_label.setText("Models loaded. Click 'Start Camera' to begin.")
        except Exception as e:
            self.message_label.setText(f"Note: Face detection not available.\nYou can still capture images.\n\nError: {str(e)[:50]}")
            self.face_detector = None
    
    def toggle_camera(self):
        """Start or stop the camera."""
        if self.camera_thread.isRunning():
            self.camera_thread.stop()
            self.start_btn.setText("📷  Start Camera")
            self.capture_btn.setEnabled(False)
            self.video_label.clear()
            self.video_label.setText("Camera Stopped")
        else:
            self.camera_thread.start()
            self.start_btn.setText("⏹  Stop Camera")
            self.capture_btn.setEnabled(True)
            self.message_label.setText("Position your face in the frame and click Capture.\nTry different angles for better recognition.")
    
    def process_frame(self, frame):
        """Process camera frame."""
        self.current_frame = frame.copy()
        
        # Draw face detection if available
        display_frame = frame.copy()
        
        if self.face_detector is not None:
            try:
                faces = self.face_detector.get(frame)
                for face in faces:
                    bbox = face.bbox.astype(int)
                    cv2.rectangle(display_frame, (bbox[0], bbox[1]), (bbox[2], bbox[3]), (79, 70, 229), 2)
            except:
                pass
        
        # Convert to Qt format
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        scaled = qt_image.scaled(480, 360, Qt.AspectRatioMode.KeepAspectRatio)
        self.video_label.setPixmap(QPixmap.fromImage(scaled))
    
    def capture_face(self):
        """Capture current frame and extract face embedding."""
        if self.current_frame is None:
            return
        
        frame = self.current_frame.copy()
        
        # Try to get face embedding
        embedding = None
        
        if self.face_detector is not None:
            try:
                faces = self.face_detector.get(frame)
                if faces and len(faces) > 0:
                    embedding = faces[0].embedding
            except Exception as e:
                print(f"Face detection error: {e}")
        
        if embedding is not None:
            self.captured_embeddings.append(embedding)
            count = len(self.captured_embeddings)
            
            self.progress_bar.setValue(count)
            self.progress_text.setText(f"{count} / {self.required_captures} captures")
            self.message_label.setText(f"✓ Face captured! ({count}/{self.required_captures})\nTry a different angle for the next one.")
            
            # Check if enrollment complete
            if count >= self.required_captures:
                self.complete_enrollment()
        else:
            self.message_label.setText("⚠ No face detected!\nMake sure your face is clearly visible in the frame.")
    
    def complete_enrollment(self):
        """Complete the enrollment process."""
        self.camera_thread.stop()
        self.start_btn.setText("📷  Start Camera")
        self.capture_btn.setEnabled(False)
        
        # Average the embeddings
        embeddings_array = np.array(self.captured_embeddings)
        avg_embedding = np.mean(embeddings_array, axis=0)
        
        # Normalize
        avg_embedding = avg_embedding / np.linalg.norm(avg_embedding)
        
        # Save embedding
        filename = data_manager.save_student_embedding(self.student_id, avg_embedding)
        
        # Update student record
        data_manager.update_student(self.student_id, {
            'enrollment_status': 'enrolled',
            'embedding_file': filename
        })
        
        self.status_label.setText("Enrolled ✓")
        self.status_label.setStyleSheet("color: #22c55e; font-size: 14px; font-weight: 500;")
        
        self.message_label.setText("✓ Enrollment completed successfully!\n\nThe student can now be recognized during monitoring sessions.")
        
        QMessageBox.information(
            self, "Enrollment Complete",
            f"Successfully enrolled {self.student.name}!\n\nFace embedding has been saved and the student can now be recognized during sessions."
        )
    
    def reset_enrollment(self):
        """Reset enrollment progress."""
        reply = QMessageBox.question(
            self, "Reset Enrollment",
            "Are you sure you want to reset the enrollment?\nAll captured images will be discarded.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.captured_embeddings = []
            self.progress_bar.setValue(0)
            self.progress_text.setText("0 / 15 captures")
            self.message_label.setText("Enrollment reset.\nClick 'Start Camera' to begin again.")
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.camera_thread.isRunning():
            self.camera_thread.stop()
        self.closed.emit()
        super().closeEvent(event)
