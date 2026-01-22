"""
Sessions Page - Manage monitoring sessions
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QDialog, QFormLayout, QTextEdit,
    QMessageBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_manager import data_manager, Session


class CreateSessionDialog(QDialog):
    """Dialog for creating a new session."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New Session")
        self.setFixedSize(450, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #1f2937;
            }
            QLabel {
                color: #d1d5db;
                font-size: 13px;
            }
            QLineEdit, QTextEdit {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 8px;
                padding: 10px 12px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4f46e5;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Create New Session")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("e.g., Lecture 1 - Introduction")
        
        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("e.g., CS101 - Programming Fundamentals")
        
        self.room_input = QLineEdit()
        self.room_input.setPlaceholderText("e.g., Room 101")
        
        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Optional description...")
        self.description_input.setMaximumHeight(80)
        
        form_layout.addRow("Session Name *", self.name_input)
        form_layout.addRow("Course Name *", self.course_input)
        form_layout.addRow("Room Number", self.room_input)
        form_layout.addRow("Description", self.description_input)
        
        layout.addLayout(form_layout)
        layout.addStretch()
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        self.create_btn = QPushButton("Create Session")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        self.create_btn.clicked.connect(self.create_session)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.create_btn)
        
        layout.addLayout(btn_layout)
    
    def create_session(self):
        """Create the session."""
        name = self.name_input.text().strip()
        course = self.course_input.text().strip()
        
        if not name or not course:
            QMessageBox.warning(self, "Error", "Session name and course are required!")
            return
        
        session = Session(
            id="",
            name=name,
            course_name=course,
            room_number=self.room_input.text().strip(),
            description=self.description_input.toPlainText().strip()
        )
        
        data_manager.add_session(session)
        self.accept()


class SessionCard(QFrame):
    """Session card widget."""
    
    def __init__(self, session, on_monitor=None, on_analytics=None, on_delete=None):
        super().__init__()
        
        self.session = session
        self.on_monitor = on_monitor
        self.on_analytics = on_analytics
        self.on_delete = on_delete
        
        status_config = {
            "created": {"color": "#6b7280", "bg": "#374151", "label": "Created"},
            "running": {"color": "#22c55e", "bg": "#14532d", "label": "Running"},
            "paused": {"color": "#eab308", "bg": "#713f12", "label": "Paused"},
            "completed": {"color": "#3b82f6", "bg": "#1e3a8a", "label": "Completed"},
        }
        
        status = status_config.get(session.status, status_config["created"])
        
        self.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        self.setFixedHeight(180)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        title = QLabel(session.name)
        title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        status_label = QLabel(status["label"])
        status_label.setStyleSheet(f"""
            QLabel {{
                background-color: {status["bg"]};
                color: {status["color"]};
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 12px;
                font-weight: 500;
            }}
        """)
        header_layout.addWidget(status_label)
        
        layout.addLayout(header_layout)
        
        # Course name
        course_label = QLabel(session.course_name)
        course_label.setStyleSheet("color: #9ca3af; font-size: 14px;")
        layout.addWidget(course_label)
        
        # Info row
        info_layout = QHBoxLayout()
        info_layout.setSpacing(24)
        
        if session.room_number:
            room_label = QLabel(f"📍 {session.room_number}")
            room_label.setStyleSheet("color: #6b7280; font-size: 13px;")
            info_layout.addWidget(room_label)
        
        date_label = QLabel(f"📅 {session.created_at[:10]}")
        date_label.setStyleSheet("color: #6b7280; font-size: 13px;")
        info_layout.addWidget(date_label)
        
        if session.duration_seconds > 0:
            mins = session.duration_seconds // 60
            duration_label = QLabel(f"⏱ {mins}m")
            duration_label.setStyleSheet("color: #6b7280; font-size: 13px;")
            info_layout.addWidget(duration_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        layout.addStretch()
        
        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(8)
        
        if session.status in ["created", "paused"]:
            monitor_btn = QPushButton("▶  Start Monitor")
            monitor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #22c55e;
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #16a34a;
                }
            """)
            monitor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            monitor_btn.clicked.connect(lambda: self.on_monitor(session) if self.on_monitor else None)
            actions_layout.addWidget(monitor_btn)
        
        elif session.status == "running":
            monitor_btn = QPushButton("🎬  View Monitor")
            monitor_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4f46e5;
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #4338ca;
                }
            """)
            monitor_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            monitor_btn.clicked.connect(lambda: self.on_monitor(session) if self.on_monitor else None)
            actions_layout.addWidget(monitor_btn)
        
        elif session.status == "completed":
            analytics_btn = QPushButton("📊  View Analytics")
            analytics_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3b82f6;
                    color: #ffffff;
                    border: none;
                    border-radius: 8px;
                    padding: 10px 16px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #2563eb;
                }
            """)
            analytics_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            analytics_btn.clicked.connect(lambda: self.on_analytics(session) if self.on_analytics else None)
            actions_layout.addWidget(analytics_btn)
        
        actions_layout.addStretch()
        
        delete_btn = QPushButton("🗑")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                color: #fca5a5;
                border: none;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #991b1b;
            }
        """)
        delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_btn.clicked.connect(lambda: self.on_delete(session) if self.on_delete else None)
        actions_layout.addWidget(delete_btn)
        
        layout.addLayout(actions_layout)


class SessionsPage(QWidget):
    """Sessions management page."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the sessions page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Sessions")
        title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Manage classroom monitoring sessions")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # Create session button
        create_btn = QPushButton("  ➕  New Session")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        create_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        create_btn.clicked.connect(self.show_create_dialog)
        header_layout.addWidget(create_btn)
        
        layout.addLayout(header_layout)
        
        # Sessions grid in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        
        self.sessions_grid = QGridLayout(scroll_content)
        self.sessions_grid.setSpacing(16)
        self.sessions_grid.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        
        # Load initial data
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh sessions from CSV."""
        # Clear existing cards
        while self.sessions_grid.count():
            child = self.sessions_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        sessions = data_manager.get_sessions()
        
        if not sessions:
            no_sessions = QLabel("No sessions yet. Click 'New Session' to create your first session!")
            no_sessions.setStyleSheet("color: #6b7280; font-size: 14px; padding: 40px;")
            no_sessions.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_grid.addWidget(no_sessions, 0, 0)
            return
        
        # Add session cards in grid (3 columns)
        for i, session in enumerate(sessions):
            row = i // 3
            col = i % 3
            
            card = SessionCard(
                session,
                on_monitor=self.open_monitor,
                on_analytics=self.open_analytics,
                on_delete=self.delete_session
            )
            self.sessions_grid.addWidget(card, row, col)
    
    def show_create_dialog(self):
        """Show the create session dialog."""
        dialog = CreateSessionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def open_monitor(self, session):
        """Open session monitor."""
        main_window = self.window()
        main_window.show_session_monitor(session.id)
    
    def open_analytics(self, session):
        """Open session analytics."""
        main_window = self.window()
        main_window.show_analytics(session.id)
    
    def delete_session(self, session):
        """Delete a session."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete session '{session.name}'?\n\nThis will also delete all related events and analytics data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            data_manager.delete_session(session.id)
            self.refresh_data()
