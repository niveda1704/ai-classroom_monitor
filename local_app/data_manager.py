"""
Data Manager - CSV-based local storage for AI Classroom Monitor
Handles all data operations for students, sessions, events, and analytics
"""

import os
import csv
import json
import uuid
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field


# Data directory setup
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
EMBEDDINGS_DIR = BASE_DIR / "embeddings"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
EMBEDDINGS_DIR.mkdir(exist_ok=True)

# CSV file paths
STUDENTS_FILE = DATA_DIR / "students.csv"
SESSIONS_FILE = DATA_DIR / "sessions.csv"
EVENTS_FILE = DATA_DIR / "events.csv"
ATTENTION_LOGS_FILE = DATA_DIR / "attention_logs.csv"
SETTINGS_FILE = DATA_DIR / "settings.json"


@dataclass
class Student:
    id: str
    name: str
    student_id: str
    email: str = ""
    course: str = ""
    department: str = ""
    enrollment_status: str = "not_enrolled"  # not_enrolled, in_progress, enrolled
    embedding_file: str = ""
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()


@dataclass
class Session:
    id: str
    name: str
    course_name: str
    room_number: str = ""
    description: str = ""
    status: str = "created"  # created, running, paused, completed
    duration_seconds: int = 0
    peak_students: int = 0
    avg_attention: float = 0.0
    total_events: int = 0
    created_at: str = ""
    started_at: str = ""
    completed_at: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class Event:
    id: str
    session_id: str
    student_id: str = ""
    student_name: str = ""
    track_id: int = 0
    event_type: str = ""  # phone_detected, poor_posture, looking_away, attention_drop, student_identified
    details: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class AttentionLog:
    id: str
    session_id: str
    student_id: str = ""
    student_name: str = ""
    track_id: int = 0
    attention_score: float = 0.0
    emotion: str = ""
    gaze_direction: str = ""
    posture: str = ""
    phone_detected: bool = False
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DataManager:
    """
    Manages all CSV-based data operations for the local application.
    Thread-safe and provides simple CRUD operations.
    """
    
    def __init__(self):
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Initialize CSV files with headers if they don't exist."""
        # Students CSV
        if not STUDENTS_FILE.exists():
            with open(STUDENTS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'name', 'student_id', 'email', 'course', 'department',
                    'enrollment_status', 'embedding_file', 'created_at', 'updated_at'
                ])
        
        # Sessions CSV
        if not SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'name', 'course_name', 'room_number', 'description',
                    'status', 'duration_seconds', 'peak_students', 'avg_attention',
                    'total_events', 'created_at', 'started_at', 'completed_at'
                ])
        
        # Events CSV
        if not EVENTS_FILE.exists():
            with open(EVENTS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'session_id', 'student_id', 'student_name', 'track_id',
                    'event_type', 'details', 'timestamp'
                ])
        
        # Attention Logs CSV
        if not ATTENTION_LOGS_FILE.exists():
            with open(ATTENTION_LOGS_FILE, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'id', 'session_id', 'student_id', 'student_name', 'track_id',
                    'attention_score', 'emotion', 'gaze_direction', 'posture',
                    'phone_detected', 'timestamp'
                ])
    
    # ===================== STUDENTS =====================
    
    def get_students(self, search: str = "") -> List[Student]:
        """Get all students, optionally filtered by search term."""
        students = []
        if not STUDENTS_FILE.exists():
            return students
        
        with open(STUDENTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                student = Student(**row)
                if search:
                    if search.lower() in student.name.lower() or \
                       search.lower() in student.student_id.lower():
                        students.append(student)
                else:
                    students.append(student)
        
        return students
    
    def get_student(self, student_id: str) -> Optional[Student]:
        """Get a single student by ID."""
        students = self.get_students()
        for s in students:
            if s.id == student_id:
                return s
        return None
    
    def add_student(self, student: Student) -> Student:
        """Add a new student."""
        with open(STUDENTS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                student.id, student.name, student.student_id, student.email,
                student.course, student.department, student.enrollment_status,
                student.embedding_file, student.created_at, student.updated_at
            ])
        return student
    
    def update_student(self, student_id: str, updates: Dict) -> Optional[Student]:
        """Update a student's information."""
        students = self.get_students()
        updated_student = None
        
        for i, s in enumerate(students):
            if s.id == student_id:
                for key, value in updates.items():
                    if hasattr(s, key):
                        setattr(s, key, value)
                s.updated_at = datetime.now().isoformat()
                updated_student = s
                break
        
        if updated_student:
            self._save_students(students)
        
        return updated_student
    
    def delete_student(self, student_id: str) -> bool:
        """Delete a student and their embedding file."""
        students = self.get_students()
        original_len = len(students)
        
        # Find and remove student
        student_to_delete = None
        for s in students:
            if s.id == student_id:
                student_to_delete = s
                break
        
        if student_to_delete:
            students.remove(student_to_delete)
            
            # Delete embedding file if exists
            if student_to_delete.embedding_file:
                embedding_path = EMBEDDINGS_DIR / student_to_delete.embedding_file
                if embedding_path.exists():
                    embedding_path.unlink()
            
            self._save_students(students)
            return True
        
        return False
    
    def _save_students(self, students: List[Student]):
        """Save all students to CSV (overwrites file)."""
        with open(STUDENTS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'name', 'student_id', 'email', 'course', 'department',
                'enrollment_status', 'embedding_file', 'created_at', 'updated_at'
            ])
            for s in students:
                writer.writerow([
                    s.id, s.name, s.student_id, s.email, s.course, s.department,
                    s.enrollment_status, s.embedding_file, s.created_at, s.updated_at
                ])
    
    def get_enrolled_students(self) -> List[Student]:
        """Get students with completed enrollment."""
        return [s for s in self.get_students() if s.enrollment_status == 'enrolled']
    
    def get_student_embeddings(self) -> List[Dict]:
        """Get all enrolled students with their embeddings for recognition."""
        embeddings = []
        for student in self.get_enrolled_students():
            if student.embedding_file:
                embedding_path = EMBEDDINGS_DIR / student.embedding_file
                if embedding_path.exists():
                    embedding = np.load(embedding_path)
                    embeddings.append({
                        'student_id': student.id,
                        'student_name': student.name,
                        'embedding': embedding
                    })
        return embeddings
    
    def save_student_embedding(self, student_id: str, embedding: np.ndarray) -> str:
        """Save student embedding to .npy file."""
        filename = f"{student_id}_embedding.npy"
        filepath = EMBEDDINGS_DIR / filename
        np.save(filepath, embedding)
        return filename
    
    # ===================== SESSIONS =====================
    
    def get_sessions(self, status: str = None, limit: int = None) -> List[Session]:
        """Get all sessions, optionally filtered by status."""
        sessions = []
        if not SESSIONS_FILE.exists():
            return sessions
        
        with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Convert numeric fields
                row['duration_seconds'] = int(row.get('duration_seconds', 0) or 0)
                row['peak_students'] = int(row.get('peak_students', 0) or 0)
                row['avg_attention'] = float(row.get('avg_attention', 0) or 0)
                row['total_events'] = int(row.get('total_events', 0) or 0)
                
                session = Session(**row)
                if status:
                    if session.status == status:
                        sessions.append(session)
                else:
                    sessions.append(session)
        
        # Sort by created_at descending
        sessions.sort(key=lambda x: x.created_at, reverse=True)
        
        if limit:
            sessions = sessions[:limit]
        
        return sessions
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a single session by ID."""
        sessions = self.get_sessions()
        for s in sessions:
            if s.id == session_id:
                return s
        return None
    
    def add_session(self, session: Session) -> Session:
        """Add a new session."""
        with open(SESSIONS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                session.id, session.name, session.course_name, session.room_number,
                session.description, session.status, session.duration_seconds,
                session.peak_students, session.avg_attention, session.total_events,
                session.created_at, session.started_at, session.completed_at
            ])
        return session
    
    def update_session(self, session_id: str, updates: Dict) -> Optional[Session]:
        """Update a session's information."""
        sessions = self.get_sessions()
        updated_session = None
        
        for i, s in enumerate(sessions):
            if s.id == session_id:
                for key, value in updates.items():
                    if hasattr(s, key):
                        setattr(s, key, value)
                updated_session = s
                break
        
        if updated_session:
            self._save_sessions(sessions)
        
        return updated_session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete a session and its related events."""
        sessions = self.get_sessions()
        original_len = len(sessions)
        
        sessions = [s for s in sessions if s.id != session_id]
        
        if len(sessions) < original_len:
            self._save_sessions(sessions)
            # Also delete related events
            self._delete_session_events(session_id)
            return True
        
        return False
    
    def _save_sessions(self, sessions: List[Session]):
        """Save all sessions to CSV (overwrites file)."""
        with open(SESSIONS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'name', 'course_name', 'room_number', 'description',
                'status', 'duration_seconds', 'peak_students', 'avg_attention',
                'total_events', 'created_at', 'started_at', 'completed_at'
            ])
            for s in sessions:
                writer.writerow([
                    s.id, s.name, s.course_name, s.room_number, s.description,
                    s.status, s.duration_seconds, s.peak_students, s.avg_attention,
                    s.total_events, s.created_at, s.started_at, s.completed_at
                ])
    
    # ===================== EVENTS =====================
    
    def get_events(self, session_id: str = None, limit: int = None) -> List[Event]:
        """Get events, optionally filtered by session."""
        events = []
        if not EVENTS_FILE.exists():
            return events
        
        with open(EVENTS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                row['track_id'] = int(row.get('track_id', 0) or 0)
                event = Event(**row)
                if session_id:
                    if event.session_id == session_id:
                        events.append(event)
                else:
                    events.append(event)
        
        # Sort by timestamp descending
        events.sort(key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            events = events[:limit]
        
        return events
    
    def add_event(self, event: Event) -> Event:
        """Add a new event."""
        with open(EVENTS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                event.id, event.session_id, event.student_id, event.student_name,
                event.track_id, event.event_type, event.details, event.timestamp
            ])
        return event
    
    def _delete_session_events(self, session_id: str):
        """Delete all events for a session."""
        events = self.get_events()
        events = [e for e in events if e.session_id != session_id]
        
        with open(EVENTS_FILE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'id', 'session_id', 'student_id', 'student_name', 'track_id',
                'event_type', 'details', 'timestamp'
            ])
            for e in events:
                writer.writerow([
                    e.id, e.session_id, e.student_id, e.student_name,
                    e.track_id, e.event_type, e.details, e.timestamp
                ])
    
    # ===================== ATTENTION LOGS =====================
    
    def add_attention_log(self, log: AttentionLog) -> AttentionLog:
        """Add a new attention log entry."""
        with open(ATTENTION_LOGS_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                log.id, log.session_id, log.student_id, log.student_name,
                log.track_id, log.attention_score, log.emotion, log.gaze_direction,
                log.posture, log.phone_detected, log.timestamp
            ])
        return log
    
    def get_attention_logs(self, session_id: str) -> List[AttentionLog]:
        """Get attention logs for a session."""
        logs = []
        if not ATTENTION_LOGS_FILE.exists():
            return logs
        
        with open(ATTENTION_LOGS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('session_id') == session_id:
                    row['track_id'] = int(row.get('track_id', 0) or 0)
                    row['attention_score'] = float(row.get('attention_score', 0) or 0)
                    row['phone_detected'] = row.get('phone_detected', 'False') == 'True'
                    logs.append(AttentionLog(**row))
        
        return logs
    
    def get_session_analytics(self, session_id: str) -> Dict:
        """Compute analytics for a session from attention logs."""
        logs = self.get_attention_logs(session_id)
        events = self.get_events(session_id)
        session = self.get_session(session_id)
        
        if not logs:
            return {
                'session': session,
                'avg_attention': 0,
                'peak_students': 0,
                'total_events': len(events),
                'phone_events': 0,
                'posture_events': 0,
                'gaze_events': 0,
                'timeline': [],
                'student_analytics': []
            }
        
        # Overall metrics
        attention_scores = [log.attention_score for log in logs]
        avg_attention = sum(attention_scores) / len(attention_scores) if attention_scores else 0
        
        # Event counts
        phone_events = len([e for e in events if e.event_type == 'phone_detected'])
        posture_events = len([e for e in events if e.event_type == 'poor_posture'])
        gaze_events = len([e for e in events if e.event_type == 'looking_away'])
        
        # Per-student analytics
        student_data = {}
        for log in logs:
            key = log.student_id or f"track_{log.track_id}"
            if key not in student_data:
                student_data[key] = {
                    'name': log.student_name or f"Track {log.track_id}",
                    'student_id': log.student_id,
                    'attention_scores': [],
                    'phone_events': 0,
                    'posture_events': 0,
                    'gaze_events': 0
                }
            student_data[key]['attention_scores'].append(log.attention_score)
        
        # Count events per student
        for event in events:
            key = event.student_id or f"track_{event.track_id}"
            if key in student_data:
                if event.event_type == 'phone_detected':
                    student_data[key]['phone_events'] += 1
                elif event.event_type == 'poor_posture':
                    student_data[key]['posture_events'] += 1
                elif event.event_type == 'looking_away':
                    student_data[key]['gaze_events'] += 1
        
        student_analytics = []
        for key, data in student_data.items():
            scores = data['attention_scores']
            student_analytics.append({
                'name': data['name'],
                'studentId': data['student_id'],
                'avgAttention': sum(scores) / len(scores) if scores else 0,
                'phoneEvents': data['phone_events'],
                'postureEvents': data['posture_events'],
                'gazeEvents': data['gaze_events']
            })
        
        # Sort by attention score
        student_analytics.sort(key=lambda x: x['avgAttention'], reverse=True)
        
        return {
            'session': session,
            'avg_attention': avg_attention,
            'peak_students': session.peak_students if session else 0,
            'total_events': len(events),
            'phone_events': phone_events,
            'posture_events': posture_events,
            'gaze_events': gaze_events,
            'timeline': [],  # Could be computed from logs grouped by time
            'student_analytics': student_analytics
        }
    
    # ===================== STATISTICS =====================
    
    def get_dashboard_stats(self) -> Dict:
        """Get statistics for dashboard."""
        students = self.get_students()
        sessions = self.get_sessions()
        
        return {
            'total_students': len(students),
            'enrolled_students': len([s for s in students if s.enrollment_status == 'enrolled']),
            'total_sessions': len(sessions),
            'active_sessions': len([s for s in sessions if s.status == 'running']),
            'recent_sessions': self.get_sessions(limit=5)
        }


# Global data manager instance
data_manager = DataManager()
