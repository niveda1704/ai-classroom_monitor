"""
Analytics Window - Session analytics and reports
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QFileDialog, QScrollArea, QGridLayout,
    QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import csv
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_manager import data_manager


class StatCard(QFrame):
    """Statistics card for analytics."""
    
    def __init__(self, icon: str, label: str, value: str, sub_value: str = "", color: str = "primary"):
        super().__init__()
        
        colors = {
            "primary": ("#818cf8", "#312e81"),
            "green": ("#34d399", "#14532d"),
            "yellow": ("#fbbf24", "#713f12"),
            "blue": ("#60a5fa", "#1e3a8a"),
            "red": ("#f87171", "#7f1d1d"),
        }
        
        fg_color, bg_color = colors.get(color, colors["primary"])
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1f2937;
                border-radius: 12px;
            }}
        """)
        self.setFixedHeight(140)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)
        
        # Header with icon
        header = QHBoxLayout()
        
        icon_frame = QFrame()
        icon_frame.setFixedSize(48, 48)
        icon_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 12px;
            }}
        """)
        icon_layout = QVBoxLayout(icon_frame)
        icon_layout.setContentsMargins(0, 0, 0, 0)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 20px; color: {fg_color};")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_layout.addWidget(icon_label)
        
        header.addWidget(icon_frame)
        header.addStretch()
        
        layout.addLayout(header)
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet("color: #ffffff; font-size: 28px; font-weight: bold;")
        layout.addWidget(value_label)
        
        # Label
        label_widget = QLabel(label)
        label_widget.setStyleSheet("color: #9ca3af; font-size: 13px;")
        layout.addWidget(label_widget)
        
        if sub_value:
            sub_label = QLabel(sub_value)
            sub_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            layout.addWidget(sub_label)


class AnalyticsWindow(QMainWindow):
    """Session analytics window."""
    
    def __init__(self, session_id: str):
        super().__init__()
        self.session_id = session_id
        self.session = data_manager.get_session(session_id)
        self.analytics = data_manager.get_session_analytics(session_id)
        self.events = data_manager.get_events(session_id)
        
        if not self.session:
            return
        
        self.setWindowTitle(f"Analytics: {self.session.name}")
        self.setMinimumSize(1200, 800)
        self.setStyleSheet("background-color: #111827;")
        
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the analytics UI."""
        central = QWidget()
        self.setCentralWidget(central)
        
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
        
        # Header
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Back to Sessions")
        back_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9ca3af;
                border: none;
                font-size: 14px;
                padding: 8px 0;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.close)
        header_layout.addWidget(back_btn)
        
        header_layout.addStretch()
        
        # Export buttons
        export_csv_btn = QPushButton("📄  Export CSV")
        export_csv_btn.setStyleSheet("""
            QPushButton {
                background-color: #374151;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #4b5563;
            }
        """)
        export_csv_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        export_csv_btn.clicked.connect(self.export_csv)
        header_layout.addWidget(export_csv_btn)
        
        main_layout.addLayout(header_layout)
        
        # Session info
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        info_layout.setContentsMargins(24, 20, 24, 20)
        
        # Title and details
        title_layout = QVBoxLayout()
        
        title = QLabel(self.session.name)
        title.setStyleSheet("color: #ffffff; font-size: 22px; font-weight: bold;")
        title_layout.addWidget(title)
        
        details = QLabel(f"{self.session.course_name} • {self.session.created_at[:10]}")
        details.setStyleSheet("color: #9ca3af; font-size: 14px;")
        title_layout.addWidget(details)
        
        info_layout.addLayout(title_layout)
        info_layout.addStretch()
        
        # Duration badge
        duration_mins = self.session.duration_seconds // 60
        duration_badge = QLabel(f"⏱ {duration_mins} minutes")
        duration_badge.setStyleSheet("""
            QLabel {
                background-color: #312e81;
                color: #818cf8;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        info_layout.addWidget(duration_badge)
        
        main_layout.addWidget(info_frame)
        
        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background: transparent;")
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(24)
        
        # Stats cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(16)
        
        avg_attention = self.analytics.get('avg_attention', 0)
        peak_students = self.analytics.get('peak_students', self.session.peak_students)
        total_events = len(self.events)
        phone_events = len([e for e in self.events if e.event_type == 'phone_detected'])
        posture_events = len([e for e in self.events if e.event_type == 'poor_posture'])
        gaze_events = len([e for e in self.events if e.event_type == 'looking_away'])
        
        stats_layout.addWidget(StatCard("👁", "Avg Attention", f"{avg_attention:.1f}%", "", "green"))
        stats_layout.addWidget(StatCard("👥", "Peak Students", str(peak_students), "", "primary"))
        stats_layout.addWidget(StatCard("📱", "Phone Events", str(phone_events), "", "red"))
        stats_layout.addWidget(StatCard("🪑", "Posture Events", str(posture_events), "", "yellow"))
        stats_layout.addWidget(StatCard("👀", "Gaze Events", str(gaze_events), "", "blue"))
        
        content_layout.addLayout(stats_layout)
        
        # Two-column layout
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(24)
        
        # Event distribution
        dist_frame = QFrame()
        dist_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        dist_layout = QVBoxLayout(dist_frame)
        dist_layout.setContentsMargins(20, 20, 20, 20)
        dist_layout.setSpacing(16)
        
        dist_title = QLabel("Event Distribution")
        dist_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        dist_layout.addWidget(dist_title)
        
        # Simple text-based distribution
        event_types = [
            ("📱 Phone Usage", phone_events, "#ef4444"),
            ("🪑 Poor Posture", posture_events, "#f97316"),
            ("👀 Looking Away", gaze_events, "#eab308"),
            ("📊 Other", total_events - phone_events - posture_events - gaze_events, "#6b7280")
        ]
        
        for label, count, color in event_types:
            row = QHBoxLayout()
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #d1d5db; font-size: 14px;")
            row.addWidget(label_widget)
            
            row.addStretch()
            
            count_widget = QLabel(str(count))
            count_widget.setStyleSheet(f"color: {color}; font-size: 16px; font-weight: bold;")
            row.addWidget(count_widget)
            
            # Simple bar
            bar_container = QFrame()
            bar_container.setFixedSize(100, 8)
            bar_container.setStyleSheet("background-color: #374151; border-radius: 4px;")
            
            if total_events > 0:
                bar_width = int((count / total_events) * 100)
                bar = QFrame(bar_container)
                bar.setGeometry(0, 0, bar_width, 8)
                bar.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
            
            row.addWidget(bar_container)
            
            dist_layout.addLayout(row)
        
        dist_layout.addStretch()
        columns_layout.addWidget(dist_frame, stretch=1)
        
        # Session summary
        summary_frame = QFrame()
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(20, 20, 20, 20)
        summary_layout.setSpacing(16)
        
        summary_title = QLabel("Session Summary")
        summary_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        summary_layout.addWidget(summary_title)
        
        # Summary items
        summary_items = [
            ("Session Name", self.session.name),
            ("Course", self.session.course_name),
            ("Room", self.session.room_number or "N/A"),
            ("Date", self.session.created_at[:10]),
            ("Duration", f"{duration_mins} minutes"),
            ("Total Events", str(total_events)),
            ("Students Detected", str(peak_students)),
            ("Avg Attention", f"{avg_attention:.1f}%"),
        ]
        
        for label, value in summary_items:
            row = QHBoxLayout()
            
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #9ca3af; font-size: 13px;")
            row.addWidget(label_widget)
            
            row.addStretch()
            
            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: 500;")
            row.addWidget(value_widget)
            
            summary_layout.addLayout(row)
        
        summary_layout.addStretch()
        columns_layout.addWidget(summary_frame, stretch=1)
        
        content_layout.addLayout(columns_layout)
        
        # Student performance table
        table_frame = QFrame()
        table_frame.setStyleSheet("""
            QFrame {
                background-color: #1f2937;
                border-radius: 12px;
            }
        """)
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(20, 20, 20, 20)
        table_layout.setSpacing(16)
        
        table_title = QLabel("Student Performance")
        table_title.setStyleSheet("color: #ffffff; font-size: 16px; font-weight: 600;")
        table_layout.addWidget(table_title)
        
        self.student_table = QTableWidget()
        self.student_table.setColumnCount(6)
        self.student_table.setHorizontalHeaderLabels([
            "Student", "Avg Attention", "Phone Events", "Posture Events", "Gaze Events", "Time in Frame"
        ])
        
        header = self.student_table.horizontalHeader()
        header.setStyleSheet("""
            QHeaderView::section {
                background-color: #1f2937;
                color: #9ca3af;
                font-weight: bold;
                padding: 12px;
                border: none;
                border-bottom: 1px solid #374151;
            }
        """)
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        
        self.student_table.verticalHeader().setVisible(False)
        self.student_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.student_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.student_table.setStyleSheet("""
            QTableWidget {
                background-color: #1f2937;
                border: none;
                gridline-color: #374151;
            }
            QTableWidget::item {
                padding: 10px;
                color: #ffffff;
                border-bottom: 1px solid #374151;
            }
            QTableWidget::item:selected {
                background-color: #4f46e5;
            }
        """)
        
        # Populate table
        student_analytics = self.analytics.get('student_analytics', [])
        self.student_table.setRowCount(len(student_analytics))
        
        for row, student in enumerate(student_analytics):
            self.student_table.setItem(row, 0, QTableWidgetItem(student.get('name', 'Unknown')))
            
            attention = student.get('avgAttention', 0)
            attention_item = QTableWidgetItem(f"{attention:.1f}%")
            if attention >= 70:
                attention_item.setForeground(QColor("#22c55e"))
            elif attention >= 40:
                attention_item.setForeground(QColor("#eab308"))
            else:
                attention_item.setForeground(QColor("#ef4444"))
            self.student_table.setItem(row, 1, attention_item)
            
            self.student_table.setItem(row, 2, QTableWidgetItem(str(student.get('phoneEvents', 0))))
            self.student_table.setItem(row, 3, QTableWidgetItem(str(student.get('postureEvents', 0))))
            self.student_table.setItem(row, 4, QTableWidgetItem(str(student.get('gazeEvents', 0))))
            self.student_table.setItem(row, 5, QTableWidgetItem("N/A"))
            
            self.student_table.setRowHeight(row, 48)
        
        table_layout.addWidget(self.student_table)
        
        content_layout.addWidget(table_frame)
        content_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
    
    def export_csv(self):
        """Export analytics to CSV."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Analytics",
            f"session_{self.session.name}_{datetime.now().strftime('%Y%m%d')}.csv",
            "CSV Files (*.csv)"
        )
        
        if not filename:
            return
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Session info
            writer.writerow(["Session Analytics Report"])
            writer.writerow([])
            writer.writerow(["Session Name", self.session.name])
            writer.writerow(["Course", self.session.course_name])
            writer.writerow(["Date", self.session.created_at[:10]])
            writer.writerow(["Duration (minutes)", self.session.duration_seconds // 60])
            writer.writerow([])
            
            # Summary stats
            writer.writerow(["Summary Statistics"])
            writer.writerow(["Average Attention", f"{self.analytics.get('avg_attention', 0):.1f}%"])
            writer.writerow(["Peak Students", self.session.peak_students])
            writer.writerow(["Total Events", len(self.events)])
            writer.writerow([])
            
            # Student performance
            writer.writerow(["Student Performance"])
            writer.writerow(["Student", "Avg Attention", "Phone Events", "Posture Events", "Gaze Events"])
            
            for student in self.analytics.get('student_analytics', []):
                writer.writerow([
                    student.get('name', 'Unknown'),
                    f"{student.get('avgAttention', 0):.1f}%",
                    student.get('phoneEvents', 0),
                    student.get('postureEvents', 0),
                    student.get('gazeEvents', 0)
                ])
            
            writer.writerow([])
            
            # Events log
            writer.writerow(["Events Log"])
            writer.writerow(["Time", "Student", "Event Type", "Details"])
            
            for event in self.events:
                writer.writerow([
                    event.timestamp,
                    event.student_name or f"Track {event.track_id}",
                    event.event_type,
                    event.details
                ])
