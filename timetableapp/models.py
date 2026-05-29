from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class ClassInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_name = db.Column(db.String(100), nullable=False)
    semester = db.Column(db.String(20), nullable=False)
    batch = db.Column(db.String(20), nullable=False)
    hall_no = db.Column(db.String(20), nullable=False)
    effect_from = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    subjects = db.relationship('Subject', backref='class_info', lazy=True)
    timetables = db.relationship('Timetable', backref='class_info', lazy=True)

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class_info.id'), nullable=False)
    course_code = db.Column(db.String(20), nullable=False)
    course_title = db.Column(db.String(100), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    is_lab = db.Column(db.Boolean, default=False)
    embedded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    timetable_entries = db.relationship('TimetableEntry', backref='subject', lazy=True)
    faculty = db.relationship('Faculty', backref='subjects')

class Faculty(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    email = db.Column(db.String(120), unique=True)
    department = db.Column(db.String(100))
    max_hours_per_day = db.Column(db.Integer, default=6)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    timetable_entries = db.relationship('TimetableEntry', backref='faculty', lazy=True)

class Timetable(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    class_id = db.Column(db.Integer, db.ForeignKey('class_info.id'), nullable=False)
    version = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Relationships
    entries = db.relationship('TimetableEntry', backref='timetable', lazy=True)

class TimetableEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timetable_id = db.Column(db.Integer, db.ForeignKey('timetable.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    period = db.Column(db.Integer, nullable=False)  # Period number in the day (e.g., 1-7)
    day = db.Column(db.String(10), nullable=False)  # Day of the week
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add unique constraint to prevent conflicts
    __table_args__ = (
        db.UniqueConstraint('timetable_id', 'day', 'period', name='unique_period_per_day'),
        db.UniqueConstraint('timetable_id', 'day', 'period', 'faculty_id', name='unique_faculty_per_period'),
    ) 