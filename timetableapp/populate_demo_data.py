# from app import app, db # Remove this line
from .models import User, Faculty, Subject, ClassInfo, Timetable, TimetableEntry
from datetime import datetime

def populate(app, db):
    with app.app_context():
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@ciet.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)

        # Add demo faculty
        faculty1 = Faculty(name='Dr. Smith', email='smith@ciet.com', department='CSE')
        faculty2 = Faculty(name='Prof. Johnson', email='johnson@ciet.com', department='CSE')
        faculty3 = Faculty(name='Dr. Williams', email='williams@ciet.com', department='CSE')
        db.session.add_all([faculty1, faculty2, faculty3])
        db.session.commit()

        # Add demo class info
        class_info = ClassInfo(
            class_name='CSE',
            semester='VI',
            batch='2022-2026',
            hall_no='D309',
            effect_from=datetime(2025, 5, 13)
        )
        db.session.add(class_info)
        db.session.commit()

        # Add demo subjects
        subj1 = Subject(class_id=class_info.id, course_code='MC', course_title='Microcontrollers', faculty_id=faculty1.id, credits=4, is_lab=True, embedded=True)
        subj2 = Subject(class_id=class_info.id, course_code='AI', course_title='Artificial Intelligence', faculty_id=faculty2.id, credits=5, is_lab=True, embedded=True)
        subj3 = Subject(class_id=class_info.id, course_code='CA', course_title='Computer Architecture', faculty_id=faculty3.id, credits=3, is_lab=False, embedded=False)
        subj4 = Subject(class_id=class_info.id, course_code='CN', course_title='Computer Networks', faculty_id=faculty1.id, credits=4, is_lab=False, embedded=False)
        subj5 = Subject(class_id=class_info.id, course_code='DS', course_title='Data Science', faculty_id=faculty2.id, credits=5, is_lab=False, embedded=False)
        subj6 = Subject(class_id=class_info.id, course_code='DAA', course_title='Design and Analysis of Algorithms', faculty_id=faculty3.id, credits=3, is_lab=False, embedded=False)
        db.session.add_all([subj1, subj2, subj3, subj4, subj5, subj6])
        db.session.commit()

        print('Demo data populated successfully!')

if __name__ == '__main__':
    # This block is typically used when running the script directly for testing.
    # In a Flask application context via CLI command, app and db would be passed.
    # For direct execution, ensure app and db are available (e.g., imported if not circular)
    # Given the circular import fix, this block might need adjustment if running directly.
    pass # Keep this simple for CLI command use

# Remove the erroneous print statement and duplicate lines below this. 