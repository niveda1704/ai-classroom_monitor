"""
Dashboard Page - Overview of classroom analytics system
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QScrollArea, QGridLayout, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_manager import data_manager


class StatCard(QFrame):
    """Statistics card widget."""
    
    def __init__(self, icon: str, label: str, value: str, sub_value: str = "", color: str = "primary"):
        super().__init__()
        
        colors = {
            "primary": ("#4f46e5", "#312e81"),
            "green": ("#22c55e", "#14532d"),
            "yellow": ("#eab308", "#713f12"),
            "blue": ("#3b82f6", "#1e3a8a"),
            "red": ("#ef4444", "#7f1d1d"),
        }
        
        fg_color, bg_color = colors.get(color, colors["primary"])
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1f2937;
                border-radius: 12px;
                padding: 8px;
            }}
        """)
        self.setFixedHeight(120)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(16)
        
        # Icon container
        icon_frame = QFrame()
        icon_frame.setFixedSize(56, 56)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
            }}
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 24px; color: {fg_color};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        layout.addWidget(icon_frame)
        
        # Text container
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #9ca3af; font-size: 14px;")
        
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
        
        text_layout.addWidget(label_widget)
        text_layout.addWidget(self.value_label)
        
        if sub_value:
            self.sub_label = QLabel(sub_value)
            self.sub_label.setStyleSheet("color: #6b7280; font-size: 12px;")
            text_layout.addWidget(self.sub_label)
        else:
            self.sub_label = None
        
        layout.addLayout(text_layout)
        layout.addStretch()
    
    def update_value(self, value: str, sub_value: str = ""):
        """Update the displayed value."""
        self.value_label.setText(value)
        if self.sub_label and sub_value:
            self.sub_label.setText(sub_value)


class RecentSessionCard(QFrame):
    """Recent session item card."""
    
    def __init__(self, session, on_click=None):
        super().__init__()
        
        status_colors = {
            "created": "#6b7280",
            "running": "#22c55e",
            "paused": "#eab308",
            "completed": "#3b82f6",
        }
        
        status_color = status_colors.get(session.status, "#6b7280")
        
        self.setStyleSheet("""
            QFrame {
                background-color: #374151;
                border-radius: 8px;
            }
            QFrame:hover {
                background-color: #4b5563;
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        
        # Status indicator
        status_dot = QLabel("●")
        status_dot.setStyleSheet(f"color: {status_color}; font-size: 10px;")
        layout.addWidget(status_dot)
        
        # Session info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(session.name)
        name_label.setStyleSheet("color: #ffffff; font-size: 14px; font-weight: 500;")
        
        details_label = QLabel(f"{session.course_name} • {session.created_at[:10]}")
        details_label.setStyleSheet("color: #9ca3af; font-size: 12px;")
        
        info_layout.addWidget(name_label)
        info_layout.addWidget(details_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Action link
        action_text = "View Analytics" if session.status == "completed" else "Monitor"
        action_btn = QLabel(f"<a style='color: #818cf8; text-decoration: none;'>{action_text}</a>")
        action_btn.setStyleSheet("font-size: 13px;")
        layout.addWidget(action_btn)
        
        self.session = session
        self.on_click = on_click
    
    def mousePressEvent(self, event):
        if self.on_click:
            self.on_click(self.session)


class DashboardPage(QWidget):
    """Dashboard page widget."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the dashboard UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Header
        header_layout = QVBoxLayout()
        title = QLabel("Dashboard")
        title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Overview of your classroom analytics system")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 14px;")
        header_layout.addWidget(title)
        header_layout.addWidget(subtitle)
        layout.addLayout(header_layout)
        
        # Stats grid
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        self.card_total_students = StatCard("👥", "Total Students", "0", "", "primary")
        self.card_enrolled = StatCard("✓", "Enrolled Students", "0", "", "green")
        self.card_sessions = StatCard("🎬", "Total Sessions", "0", "", "blue")
        self.card_active = StatCard("▶", "Active Sessions", "0", "", "yellow")
        
        stats_layout.addWidget(self.card_total_students)
        stats_layout.addWidget(self.card_enrolled)
        stats_layout.addWidget(self.card_sessions)
        stats_layout.addWidget(self.card_active)
        
        layout.addLayout(stats_layout)
        
        # Quick actions section
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(24)
        
        # Recent Sessions
        recent_frame = QFrame()
        recent_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        recent_layout = QVBoxLayout(recent_frame)
        recent_layout.setContentsMargins(20, 20, 20, 20)
        recent_layout.setSpacing(16)
        
        recent_header = QHBoxLayout()
        recent_title = QLabel("Recent Sessions")
        recent_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        
        view_all_btn = QPushButton("View All")
        view_all_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #818cf8;
                border: none;
                font-size: 13px;
            }
            QPushButton:hover {
                color: #a5b4fc;
            }
        """)
        view_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        recent_header.addWidget(view_all_btn)
        recent_layout.addLayout(recent_header)
        
        self.sessions_container = QVBoxLayout()
        self.sessions_container.setSpacing(8)
        recent_layout.addLayout(self.sessions_container)
        recent_layout.addStretch()
        
        actions_layout.addWidget(recent_frame, stretch=1)
        
        # Quick Actions
        quick_frame = QFrame()
        quick_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        quick_layout = QVBoxLayout(quick_frame)
        quick_layout.setContentsMargins(20, 20, 20, 20)
        quick_layout.setSpacing(16)
        
        quick_title = QLabel("Quick Actions")
        quick_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        quick_layout.addWidget(quick_title)
        
        btn_new_session = QPushButton("  ▶  Start New Session")
        btn_new_session.setStyleSheet("""
            QPushButton {
                background-color: #4f46e5;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4338ca;
            }
        """)
        btn_new_session.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_add_student = QPushButton("  ➕  Add New Student")
        btn_add_student.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        btn_add_student.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_view_analytics = QPushButton("  📊  View Analytics")
        btn_view_analytics.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 16px;
                font-size: 14px;
                font-weight: 500;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        btn_view_analytics.setCursor(Qt.CursorShape.PointingHandCursor)
        
        quick_layout.addWidget(btn_new_session)
        quick_layout.addWidget(btn_add_student)
        quick_layout.addWidget(btn_view_analytics)
        quick_layout.addStretch()
        
        actions_layout.addWidget(quick_frame, stretch=1)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        # Load initial data
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh dashboard data from CSV."""
        stats = data_manager.get_dashboard_stats()
        
        self.card_total_students.update_value(
            str(stats['total_students']),
            f"{stats['enrolled_students']} enrolled"
        )
        self.card_enrolled.update_value(str(stats['enrolled_students']))
        self.card_sessions.update_value(str(stats['total_sessions']))
        self.card_active.update_value(str(stats['active_sessions']))
        
        # Clear and repopulate recent sessions
        while self.sessions_container.count():
            child = self.sessions_container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        for session in stats['recent_sessions']:
            card = RecentSessionCard(session, on_click=self.on_session_click)
            self.sessions_container.addWidget(card)
        
        if not stats['recent_sessions']:
            no_sessions = QLabel("No sessions yet. Create your first session!")
            no_sessions.setStyleSheet("color: #6b7280; font-size: 14px; padding: 20px;")
            no_sessions.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.sessions_container.addWidget(no_sessions)
    
    def on_session_click(self, session):
        """Handle session card click."""
        main_window = self.window()
        if session.status == "completed":
            main_window.show_analytics(session.id)
        else:
            main_window.show_session_monitor(session.id)
