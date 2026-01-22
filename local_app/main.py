"""
AI Classroom Monitor - Local Desktop Application
Main application window with modern dark theme UI
"""

import sys
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QStackedWidget, QPushButton, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon, QFont, QPalette, QColor

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from local_app.pages.dashboard import DashboardPage
from local_app.pages.students import StudentsPage
from local_app.pages.sessions import SessionsPage


class SidebarButton(QPushButton):
    """Custom styled sidebar navigation button."""
    
    def __init__(self, text: str, icon_text: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_text}  {text}")
        self.setCheckable(True)
        self.setFixedHeight(45)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9ca3af;
                border: none;
                border-radius: 8px;
                text-align: left;
                padding-left: 12px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #374151;
                color: #ffffff;
            }
            QPushButton:checked {
                background-color: #4f46e5;
                color: #ffffff;
            }
        """)


class Sidebar(QFrame):
    """Sidebar navigation panel."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(240)
        self.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-right: 1px solid #374151;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        # Logo/Title
        logo_layout = QHBoxLayout()
        logo_icon = QLabel("🎓")
        logo_icon.setStyleSheet("font-size: 28px;")
        logo_text = QLabel("Classroom AI")
        logo_text.setStyleSheet("""
            color: #ffffff;
            font-size: 18px;
            font-weight: bold;
        """)
        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)
        logo_layout.addStretch()
        layout.addLayout(logo_layout)
        
        # Separator
        separator = QFrame()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #374151;")
        layout.addWidget(separator)
        layout.addSpacing(12)
        
        # Navigation buttons
        self.nav_buttons = []
        
        self.btn_dashboard = SidebarButton("Dashboard", "📊")
        self.btn_students = SidebarButton("Students", "👥")
        self.btn_sessions = SidebarButton("Sessions", "🎬")
        
        self.nav_buttons = [self.btn_dashboard, self.btn_students, self.btn_sessions]
        
        for btn in self.nav_buttons:
            layout.addWidget(btn)
        
        layout.addStretch()
        
        # Bottom info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #374151;
                border-radius: 8px;
                border: none;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(12, 12, 12, 12)
        
        status_label = QLabel("● Local Mode")
        status_label.setStyleSheet("color: #34d399; font-size: 12px;")
        version_label = QLabel("Version 1.0.0")
        version_label.setStyleSheet("color: #6b7280; font-size: 11px;")
        
        info_layout.addWidget(status_label)
        info_layout.addWidget(version_label)
        
        layout.addWidget(info_frame)
    
    def set_active(self, index: int):
        """Set the active navigation button."""
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Classroom Monitor")
        self.setMinimumSize(1280, 720)
        self.resize(1440, 900)
        
        # Set dark theme
        self.set_dark_theme()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Content area
        content_frame = QFrame()
        content_frame.setStyleSheet("background-color: #111827;")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Stacked widget for pages
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)
        
        # Create pages
        self.dashboard_page = DashboardPage()
        self.students_page = StudentsPage()
        self.sessions_page = SessionsPage()
        
        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.students_page)
        self.stack.addWidget(self.sessions_page)
        
        main_layout.addWidget(content_frame)
        
        # Connect navigation
        self.sidebar.btn_dashboard.clicked.connect(lambda: self.navigate_to(0))
        self.sidebar.btn_students.clicked.connect(lambda: self.navigate_to(1))
        self.sidebar.btn_sessions.clicked.connect(lambda: self.navigate_to(2))
        
        # Set initial page
        self.navigate_to(0)
    
    def set_dark_theme(self):
        """Apply dark theme to the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #111827;
            }
            QScrollArea {
                border: none;
                background-color: #111827;
            }
            QScrollBar:vertical {
                background-color: #1f2937;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4b5563;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #6b7280;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background-color: #1f2937;
                height: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:horizontal {
                background-color: #4b5563;
                border-radius: 6px;
                min-width: 20px;
            }
            QLineEdit, QTextEdit, QSpinBox, QComboBox {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 8px;
                padding: 8px 12px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #4f46e5;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 10px;
            }
            QComboBox QAbstractItemView {
                background-color: #374151;
                color: #ffffff;
                selection-background-color: #4f46e5;
            }
            QTableWidget {
                background-color: #1f2937;
                border: none;
                gridline-color: #374151;
                color: #ffffff;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #374151;
            }
            QTableWidget::item:selected {
                background-color: #4f46e5;
            }
            QHeaderView::section {
                background-color: #1f2937;
                color: #9ca3af;
                font-weight: bold;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #374151;
            }
            QMessageBox {
                background-color: #1f2937;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QDialog {
                background-color: #1f2937;
            }
        """)
    
    def navigate_to(self, index: int):
        """Navigate to a specific page."""
        self.sidebar.set_active(index)
        self.stack.setCurrentIndex(index)
        
        # Refresh page data
        if index == 0:
            self.dashboard_page.refresh_data()
        elif index == 1:
            self.students_page.refresh_data()
        elif index == 2:
            self.sessions_page.refresh_data()
    
    def show_session_monitor(self, session_id: str):
        """Open session monitor for a specific session."""
        from local_app.pages.session_monitor import SessionMonitorWindow
        self.monitor_window = SessionMonitorWindow(session_id)
        self.monitor_window.show()
    
    def show_analytics(self, session_id: str):
        """Open analytics for a specific session."""
        from local_app.pages.analytics import AnalyticsWindow
        self.analytics_window = AnalyticsWindow(session_id)
        self.analytics_window.show()
    
    def show_enrollment(self, student_id: str):
        """Open enrollment for a specific student."""
        from local_app.pages.enrollment import EnrollmentWindow
        self.enrollment_window = EnrollmentWindow(student_id)
        self.enrollment_window.closed.connect(self.students_page.refresh_data)
        self.enrollment_window.show()


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
