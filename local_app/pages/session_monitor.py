"""
Session Monitor Window - Real-time classroom monitoring
"""

import cv2
import numpy as np
import time
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QScrollArea, QGridLayout, QMessageBox,
    QSplitter
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QImage, QPixmap

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from data_manager import data_manager, Event, AttentionLog


class MonitoringThread(QThread):
    """Thread for camera and AI processing."""
    frame_ready = pyqtSignal(np.ndarray, dict)
    metrics_updated = pyqtSignal(dict)
    event_detected = pyqtSignal(dict)
    
    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.running = False
        self.cap = None
        self.pipeline = None
        self.known_embeddings = []
    
    def run(self):
        # Initialize camera
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        # Try to initialize AI pipeline
        try:
            from ai_service.pipeline import MonitoringPipeline
            self.pipeline = MonitoringPipeline(
                target_fps=8,
                known_embeddings=self.known_embeddings
            )
            self.pipeline.initialize()
            self.pipeline.start_session(self.session_id)
        except Exception as e:
            print(f"Pipeline init error: {e}")
            self.pipeline = None
        
        self.running = True
        last_process_time = 0
        process_interval = 0.125  # ~8 FPS for AI
        
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.msleep(33)
                continue
            
            current_time = time.time()
            result = {}
            
            # Process through AI pipeline at target FPS
            if self.pipeline and (current_time - last_process_time) >= process_interval:
                try:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(self.pipeline.process_frame(frame))
                    loop.close()
                    last_process_time = current_time
                    
                    # Emit metrics
                    if 'metrics' in result:
                        self.metrics_updated.emit(result['metrics'])
                    
                    # Emit events
                    if 'events' in result:
                        for event in result['events']:
                            self.event_detected.emit(event)
                    
                except Exception as e:
                    print(f"Processing error: {e}")
            
            self.frame_ready.emit(frame, result)
            self.msleep(33)  # ~30 FPS for display
    
    def stop(self):
        self.running = False
        if self.pipeline:
            try:
                self.pipeline.stop_session()
            except:
                pass
        if self.cap:
            self.cap.release()
        self.wait()
    
    def set_embeddings(self, embeddings):
        self.known_embeddings = embeddings
        if self.pipeline:
            self.pipeline.update_known_embeddings(embeddings)


class MetricCard(QFrame):
    """Small metric display card."""
    
    def __init__(self, icon: str, label: str, value: str, color: str = "primary"):
        super().__init__()
        
        colors = {
            "primary": "#818cf8",
            "green": "#34d399",
            "yellow": "#fbbf24",
            "red": "#f87171",
            "blue": "#60a5fa",
        }
        
        self.setStyleSheet("""
            QFrame {
                background-color: #374151;
                border-radius: 8px;
            }
        """)
        self.setFixedHeight(70)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        
        # Icon and value
        top_layout = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 16px; color: {colors.get(color, colors['primary'])};")
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        
        top_layout.addWidget(icon_label)
        top_layout.addStretch()
        top_layout.addWidget(self.value_label)
        
        layout.addLayout(top_layout)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #9ca3af; font-size: 11px;")
        layout.addWidget(label_widget)
    
    def set_value(self, value: str):
        self.value_label.setText(value)


class EventItem(QFrame):
    """Event list item."""
    
    def __init__(self, event: dict):
        super().__init__()
        
        event_config = {
            'phone_detected': {'icon': '📱', 'color': '#ef4444', 'bg': '#7f1d1d'},
            'poor_posture': {'icon': '🪑', 'color': '#f97316', 'bg': '#7c2d12'},
            'looking_away': {'icon': '👀', 'color': '#eab308', 'bg': '#713f12'},
            'attention_drop': {'icon': '📉', 'color': '#eab308', 'bg': '#713f12'},
            'student_identified': {'icon': '✓', 'color': '#22c55e', 'bg': '#14532d'},
        }
        
        config = event_config.get(event.get('type', ''), {'icon': '●', 'color': '#6b7280', 'bg': '#374151'})
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {config['bg']};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        icon = QLabel(config['icon'])
        icon.setStyleSheet("font-size: 14px;")
        layout.addWidget(icon)
        
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        
        name = event.get('student_name', event.get('track_id', 'Unknown'))
        event_type = event.get('type', 'event').replace('_', ' ').title()
        
        title = QLabel(f"{name} - {event_type}")
        title.setStyleSheet(f"color: {config['color']}; font-size: 12px; font-weight: 500;")
        
        time_str = datetime.now().strftime("%H:%M:%S")
        time_label = QLabel(time_str)
        time_label.setStyleSheet("color: #6b7280; font-size: 10px;")
        
        info_layout.addWidget(title)
        info_layout.addWidget(time_label)
        layout.addLayout(info_layout)
        layout.addStretch()


class StudentCard(QFrame):
    """Student status card in monitor."""
    
    def __init__(self, data: dict):
        super().__init__()
        
        attention = data.get('attention', 0)
        if attention >= 70:
            attention_color = "#22c55e"
        elif attention >= 40:
            attention_color = "#eab308"
        else:
            attention_color = "#ef4444"
        
        self.setStyleSheet("""
            QFrame {
                background-color: #374151;
                border-radius: 8px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        
        # Avatar
        name = data.get('name', f"Track {data.get('track_id', '?')}")
        avatar = QLabel(name[0].upper() if name else "?")
        avatar.setFixedSize(32, 32)
        avatar.setStyleSheet("""
            QLabel {
                background-color: #4b5563;
                color: #ffffff;
                border-radius: 16px;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(avatar)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500;")
        
        attention_label = QLabel(f"{attention:.0f}% attention")
        attention_label.setStyleSheet(f"color: {attention_color}; font-size: 11px;")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(attention_label)
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Status icons
        if data.get('phone_detected'):
            phone_icon = QLabel("📱")
            phone_icon.setStyleSheet("font-size: 14px;")
            layout.addWidget(phone_icon)
        
        if data.get('looking_away'):
            gaze_icon = QLabel("👀")
            gaze_icon.setStyleSheet("font-size: 14px;")
            layout.addWidget(gaze_icon)


class SessionMonitorWindow(QMainWindow):
    """Real-time session monitoring window."""
    
    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.session = data_manager.get_session(session_id)
        
        if not self.session:
            QMessageBox.critical(self, "Error", "Session not found!")
            self.close()
            return
        
        self.setWindowTitle(f"Monitor: {self.session.name}")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #111827;")
        
        # State
        self.elapsed_seconds = 0
        self.is_monitoring = False
        self.current_metrics = {}
        self.events = []
        self.tracked_students = {}
        
        self.setup_ui()
        
        # Monitoring thread
        self.monitor_thread = MonitoringThread(session_id)
        self.monitor_thread.frame_ready.connect(self.update_frame)
        self.monitor_thread.metrics_updated.connect(self.update_metrics)
        self.monitor_thread.event_detected.connect(self.add_event)
        
        # Load known embeddings
        embeddings = data_manager.get_student_embeddings()
        self.monitor_thread.set_embeddings(embeddings)
        
        # Timer for elapsed time
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_elapsed)
    
    def setup_ui(self):
        """Setup the monitor UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        
        # Session info
        info_layout = QVBoxLayout()
        title = QLabel(self.session.name)
        title.setStyleSheet("color: #ffffff; font-size: 20px; font-weight: bold;")
        subtitle = QLabel(f"{self.session.course_name}")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 13px;")
        info_layout.addWidget(title)
        info_layout.addWidget(subtitle)
        header_layout.addLayout(info_layout)
        
        header_layout.addStretch()
        
        # Controls
        self.start_btn = QPushButton("▶  Start Monitoring")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.clicked.connect(self.toggle_monitoring)
        header_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹  End Session")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef4444;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self.end_session)
        header_layout.addWidget(self.stop_btn)
        
        layout.addLayout(header_layout)
        
        # Main content - splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #374151;
                width: 2px;
            }
        """)
        
        # Left panel - Video and metrics
        left_panel = QFrame()
        left_panel.setStyleSheet("background-color: transparent;")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(16)
        
        # Video frame
        video_frame = QFrame()
        video_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        video_layout = QVBoxLayout(video_frame)
        video_layout.setContentsMargins(12, 12, 12, 12)
        
        self.video_label = QLabel("Camera Feed")
        self.video_label.setMinimumSize(800, 500)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: #374151;
                border-radius: 8px;
                color: #6b7280;
                font-size: 16px;
            }
        """)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        video_layout.addWidget(self.video_label)
        
        left_layout.addWidget(video_frame)
        
        # Metrics row
        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(12)
        
        self.metric_students = MetricCard("👥", "Students", "0", "primary")
        self.metric_attention = MetricCard("👁", "Avg Attention", "0%", "green")
        self.metric_events = MetricCard("⚠", "Events", "0", "yellow")
        self.metric_time = MetricCard("⏱", "Duration", "0:00", "blue")
        
        metrics_layout.addWidget(self.metric_students)
        metrics_layout.addWidget(self.metric_attention)
        metrics_layout.addWidget(self.metric_events)
        metrics_layout.addWidget(self.metric_time)
        
        left_layout.addLayout(metrics_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel - Events and students
        right_panel = QFrame()
        right_panel.setStyleSheet("background-color: transparent;")
        right_panel.setFixedWidth(320)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(16)
        
        # Events section
        events_frame = QFrame()
        events_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        events_layout = QVBoxLayout(events_frame)
        events_layout.setContentsMargins(12, 12, 12, 12)
        events_layout.setSpacing(8)
        
        events_title = QLabel("Live Events")
        events_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600;")
        events_layout.addWidget(events_title)
        
        events_scroll = QScrollArea()
        events_scroll.setWidgetResizable(True)
        events_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.events_container = QWidget()
        self.events_container.setStyleSheet("background: transparent;")
        self.events_list = QVBoxLayout(self.events_container)
        self.events_list.setContentsMargins(0, 0, 0, 0)
        self.events_list.setSpacing(6)
        self.events_list.addStretch()
        
        events_scroll.setWidget(self.events_container)
        events_layout.addWidget(events_scroll)
        
        right_layout.addWidget(events_frame, stretch=1)
        
        # Students section
        students_frame = QFrame()
        students_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        students_layout = QVBoxLayout(students_frame)
        students_layout.setContentsMargins(12, 12, 12, 12)
        students_layout.setSpacing(8)
        
        students_title = QLabel("Detected Students")
        students_title.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 600;")
        students_layout.addWidget(students_title)
        
        students_scroll = QScrollArea()
        students_scroll.setWidgetResizable(True)
        students_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        self.students_container = QWidget()
        self.students_container.setStyleSheet("background: transparent;")
        self.students_list = QVBoxLayout(self.students_container)
        self.students_list.setContentsMargins(0, 0, 0, 0)
        self.students_list.setSpacing(6)
        self.students_list.addStretch()
        
        students_scroll.setWidget(self.students_container)
        students_layout.addWidget(students_scroll)
        
        right_layout.addWidget(students_frame, stretch=1)
        
        splitter.addWidget(right_panel)
        
        layout.addWidget(splitter)
    
    def toggle_monitoring(self):
        """Start or pause monitoring."""
        if not self.is_monitoring:
            self.start_monitoring()
        else:
            self.pause_monitoring()
    
    def start_monitoring(self):
        """Start the monitoring process."""
        self.is_monitoring = True
        self.start_btn.setText("⏸  Pause")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #eab308;
                color: #000000;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ca8a04;
            }
        """)
        
        # Update session status
        data_manager.update_session(self.session_id, {
            'status': 'running',
            'started_at': datetime.now().isoformat()
        })
        
        self.monitor_thread.start()
        self.timer.start(1000)
    
    def pause_monitoring(self):
        """Pause the monitoring."""
        self.is_monitoring = False
        self.start_btn.setText("▶  Resume")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        
        data_manager.update_session(self.session_id, {'status': 'paused'})
        
        self.monitor_thread.stop()
        self.timer.stop()
    
    def end_session(self):
        """End the monitoring session."""
        reply = QMessageBox.question(
            self, "End Session",
            "Are you sure you want to end this session?\n\nAll data will be saved and you can view analytics.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.is_monitoring = False
            self.monitor_thread.stop()
            self.timer.stop()
            
            # Update session
            data_manager.update_session(self.session_id, {
                'status': 'completed',
                'completed_at': datetime.now().isoformat(),
                'duration_seconds': self.elapsed_seconds,
                'total_events': len(self.events),
                'peak_students': max([m.get('student_count', 0) for m in [self.current_metrics]] + [0])
            })
            
            self.close()
    
    def update_frame(self, frame: np.ndarray, result: dict):
        """Update the video display."""
        display_frame = frame.copy()
        
        # Draw detections if available
        if 'tracks' in result:
            for track in result['tracks']:
                bbox = track.get('bbox', [])
                if len(bbox) == 4:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    
                    # Color based on attention
                    attention = track.get('attention', 0)
                    if attention >= 70:
                        color = (0, 255, 0)
                    elif attention >= 40:
                        color = (0, 255, 255)
                    else:
                        color = (0, 0, 255)
                    
                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
                    
                    # Name label
                    name = track.get('name', f"ID:{track.get('track_id', '?')}")
                    cv2.putText(display_frame, name, (x1, y1-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Convert to Qt
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        qt_image = QImage(rgb_frame.data, w, h, ch * w, QImage.Format.Format_RGB888)
        
        scaled = qt_image.scaled(
            self.video_label.width(),
            self.video_label.height(),
            Qt.AspectRatioMode.KeepAspectRatio
        )
        self.video_label.setPixmap(QPixmap.fromImage(scaled))
        
        # Update tracked students
        if 'tracks' in result:
            self.update_students_list(result['tracks'])
    
    def update_metrics(self, metrics: dict):
        """Update metrics display."""
        self.current_metrics = metrics
        
        self.metric_students.set_value(str(metrics.get('student_count', 0)))
        self.metric_attention.set_value(f"{metrics.get('avg_attention', 0):.0f}%")
    
    def add_event(self, event: dict):
        """Add a new event to the list."""
        self.events.append(event)
        self.metric_events.set_value(str(len(self.events)))
        
        # Save to CSV
        event_obj = Event(
            id="",
            session_id=self.session_id,
            student_id=event.get('student_id', ''),
            student_name=event.get('student_name', ''),
            track_id=event.get('track_id', 0),
            event_type=event.get('type', ''),
            details=str(event.get('details', ''))
        )
        data_manager.add_event(event_obj)
        
        # Add to UI
        event_widget = EventItem(event)
        self.events_list.insertWidget(0, event_widget)
        
        # Keep only last 50 events in UI
        while self.events_list.count() > 51:
            item = self.events_list.takeAt(self.events_list.count() - 2)
            if item.widget():
                item.widget().deleteLater()
    
    def update_students_list(self, tracks: list):
        """Update the students list."""
        # Clear current list
        while self.students_list.count() > 1:
            item = self.students_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add current tracks
        for track in tracks:
            card = StudentCard(track)
            self.students_list.insertWidget(self.students_list.count() - 1, card)
    
    def update_elapsed(self):
        """Update elapsed time."""
        self.elapsed_seconds += 1
        mins = self.elapsed_seconds // 60
        secs = self.elapsed_seconds % 60
        self.metric_time.set_value(f"{mins}:{secs:02d}")
    
    def closeEvent(self, event):
        """Handle window close."""
        if self.is_monitoring:
            reply = QMessageBox.question(
                self, "Close Monitor",
                "Monitoring is still active. End the session before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.end_session()
                return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        self.monitor_thread.stop()
        self.timer.stop()
        super().closeEvent(event)
