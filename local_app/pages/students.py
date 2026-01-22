"""
Students Page - Manage student records and enrollment
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QPushButton, QLineEdit,
    QDialog, QFormLayout, QMessageBox, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data_manager import data_manager, Student


class AddStudentDialog(QDialog):
    """Dialog for adding a new student."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Student")
        self.setFixedSize(450, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #1f2937;
            }
            QLabel {
                color: #d1d5db;
                font-size: 13px;
            }
            QLineEdit {
                background-color: #374151;
                border: 1px solid #4b5563;
                border-radius: 8px;
                padding: 10px 12px;
                color: #ffffff;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #4f46e5;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Title
        title = QLabel("Add New Student")
        title.setStyleSheet("color: #ffffff; font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Form
        form_layout = QFormLayout()
        form_layout.setSpacing(12)
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter student name")
        
        self.student_id_input = QLineEdit()
        self.student_id_input.setPlaceholderText("Enter student ID")
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter email address")
        
        self.course_input = QLineEdit()
        self.course_input.setPlaceholderText("Enter course name")
        
        self.department_input = QLineEdit()
        self.department_input.setPlaceholderText("Enter department")
        
        form_layout.addRow("Full Name *", self.name_input)
        form_layout.addRow("Student ID *", self.student_id_input)
        form_layout.addRow("Email", self.email_input)
        form_layout.addRow("Course", self.course_input)
        form_layout.addRow("Department", self.department_input)
        
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
        
        self.add_btn = QPushButton("Add Student")
        self.add_btn.setStyleSheet("""
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
        self.add_btn.clicked.connect(self.add_student)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.add_btn)
        
        layout.addLayout(btn_layout)
    
    def add_student(self):
        """Add the student to the database."""
        name = self.name_input.text().strip()
        student_id = self.student_id_input.text().strip()
        
        if not name or not student_id:
            QMessageBox.warning(self, "Error", "Name and Student ID are required!")
            return
        
        student = Student(
            id="",
            name=name,
            student_id=student_id,
            email=self.email_input.text().strip(),
            course=self.course_input.text().strip(),
            department=self.department_input.text().strip()
        )
        
        data_manager.add_student(student)
        self.accept()


class StudentsPage(QWidget):
    """Students management page."""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the students page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_layout = QVBoxLayout()
        title = QLabel("Students")
        title.setStyleSheet("color: #ffffff; font-size: 24px; font-weight: bold;")
        subtitle = QLabel("Manage student records and face enrollment")
        subtitle.setStyleSheet("color: #9ca3af; font-size: 14px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout)
        
        header_layout.addStretch()
        
        # Add student button
        add_btn = QPushButton("  ➕  Add Student")
        add_btn.setStyleSheet("""
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
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.clicked.connect(self.show_add_dialog)
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Search bar
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search students...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 12px 16px;
                color: #ffffff;
                font-size: 14px;
                max-width: 300px;
            }
            QLineEdit:focus {
                border-color: #4f46e5;
            }
        """)
        self.search_input.textChanged.connect(self.filter_students)
        search_layout.addWidget(self.search_input)
        search_layout.addStretch()
        
        layout.addLayout(search_layout)
        
        # Students table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels([
            "Name", "Student ID", "Email", "Course", "Department", "Status", "Actions"
        ])
        
        # Table styling
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #1f2937;
                border: none;
                border-radius: 12px;
                gridline-color: #374151;
            }
            QTableWidget::item {
                padding: 12px;
                color: #ffffff;
            }
            QTableWidget::item:selected {
                background-color: #4f46e5;
            }
        """)
        
        header = self.table.horizontalHeader()
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
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(6, 200)
        
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        layout.addWidget(self.table)
        
        # Load initial data
        self.refresh_data()
    
    def refresh_data(self, search: str = ""):
        """Refresh student data from CSV."""
        students = data_manager.get_students(search)
        
        self.table.setRowCount(len(students))
        
        for row, student in enumerate(students):
            # Name
            name_item = QTableWidgetItem(student.name)
            self.table.setItem(row, 0, name_item)
            
            # Student ID
            id_item = QTableWidgetItem(student.student_id)
            self.table.setItem(row, 1, id_item)
            
            # Email
            email_item = QTableWidgetItem(student.email or "-")
            self.table.setItem(row, 2, email_item)
            
            # Course
            course_item = QTableWidgetItem(student.course or "-")
            self.table.setItem(row, 3, course_item)
            
            # Department
            dept_item = QTableWidgetItem(student.department or "-")
            self.table.setItem(row, 4, dept_item)
            
            # Status
            status_widget = QWidget()
            status_layout = QHBoxLayout(status_widget)
            status_layout.setContentsMargins(8, 4, 8, 4)
            
            status_colors = {
                "enrolled": ("#22c55e", "#14532d", "Enrolled"),
                "in_progress": ("#eab308", "#713f12", "In Progress"),
                "not_enrolled": ("#6b7280", "#374151", "Not Enrolled"),
            }
            
            fg, bg, text = status_colors.get(student.enrollment_status, status_colors["not_enrolled"])
            
            status_label = QLabel(text)
            status_label.setStyleSheet(f"""
                QLabel {{
                    background-color: {bg};
                    color: {fg};
                    padding: 4px 12px;
                    border-radius: 12px;
                    font-size: 12px;
                    font-weight: 500;
                }}
            """)
            status_layout.addWidget(status_label)
            status_layout.addStretch()
            
            self.table.setCellWidget(row, 5, status_widget)
            
            # Actions
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 4, 4, 4)
            actions_layout.setSpacing(8)
            
            enroll_btn = QPushButton("📷 Enroll")
            enroll_btn.setStyleSheet("""
                QPushButton {
                    background-color: #374151;
                    color: #ffffff;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 12px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #4b5563;
                }
            """)
            enroll_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            enroll_btn.clicked.connect(lambda checked, s=student: self.enroll_student(s))
            
            delete_btn = QPushButton("🗑")
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #7f1d1d;
                    color: #fca5a5;
                    border: none;
                    border-radius: 6px;
                    padding: 6px 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #991b1b;
                }
            """)
            delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            delete_btn.clicked.connect(lambda checked, s=student: self.delete_student(s))
            
            actions_layout.addWidget(enroll_btn)
            actions_layout.addWidget(delete_btn)
            actions_layout.addStretch()
            
            self.table.setCellWidget(row, 6, actions_widget)
        
        self.table.setRowHeight(0, 60)
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, 56)
    
    def filter_students(self, text: str):
        """Filter students by search text."""
        self.refresh_data(text)
    
    def show_add_dialog(self):
        """Show the add student dialog."""
        dialog = AddStudentDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_data()
    
    def enroll_student(self, student):
        """Open enrollment window for a student."""
        main_window = self.window()
        main_window.show_enrollment(student.id)
    
    def delete_student(self, student):
        """Delete a student."""
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete {student.name}?\n\nThis will also delete their face enrollment data.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            data_manager.delete_student(student.id)
            self.refresh_data()
