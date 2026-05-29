from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, ClassInfo, Subject, Faculty, Timetable, TimetableEntry
from admin import init_admin
from datetime import datetime, timedelta
import os
from werkzeug.security import generate_password_hash
from timetable_generator import TimetableGenerator

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize admin
init_admin(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.index'))
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin.index'))
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_timetable():
    try:
        data = request.get_json()
        print('--- DEBUG: Raw POST data ---')
        print(data)
        
        # Create timetable generator
        generator = TimetableGenerator()
        
        # Add sections
        for section in data.get('sections', []):
            generator.add_section(section)
        
        # Add subjects
        for subject in data.get('subjects', []):
            # Robustly parse booleans
            is_lab = subject.get('is_lab', False)
            if isinstance(is_lab, str):
                is_lab = is_lab.lower() == 'true' or is_lab == 'on'
            embedded = subject.get('embedded', False)
            if isinstance(embedded, str):
                embedded = embedded.lower() == 'true' or embedded == 'on'
            print(f"Adding subject: {subject['name']}, credits: {subject['credits']}, faculty: {subject.get('faculty', '')}, is_lab: {is_lab}, embedded: {embedded}")
            generator.add_subject(
                name=subject['name'],
                credits=int(subject['credits']),
                faculty=subject.get('faculty', ''),
                is_lab=is_lab,
                embedded=embedded
            )
        
        # Generate timetable
        generator.generate_timetable()
        print('--- DEBUG: Timetable Output ---')
        for section, grid in generator.timetables.items():
            print(f'Section: {section}')
            for day in range(5):
                print([grid[session][day] for session in range(9)])
        
        # Generate dates for each day
        num_days = data.get('num_days', 5)
        today = datetime.today()
        dates = [(today + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(num_days)]
        
        # Prepare faculty-subject mapping
        faculty_subjects = data.get('faculty_subjects', {})
        
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'timetable_{timestamp}.pdf'
        pdf_path = os.path.join('static', 'pdfs', pdf_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        
        # Pass all meta fields to PDF
        if generator.generate_pdf(
            pdf_path,
            department=data.get('department'),
            year=data.get('year'),
            faculty_subjects=faculty_subjects,
            dates=dates,
            semester=data.get('semester'),
            class_name=data.get('class_name'),
            batch=data.get('batch'),
            hall_no=data.get('hall_no'),
            wef=data.get('wef')
        ):
            return jsonify({
                'success': True,
                'message': 'Timetable generated successfully',
                'pdf_url': f'/static/pdfs/{pdf_filename}',
                'timetables': generator.timetables,
                'faculty_subjects': faculty_subjects
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to generate timetable PDF'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500

@app.route('/download/<filename>')
def download_pdf(filename):
    try:
        return send_file(
            os.path.join('static', 'pdfs', filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error downloading file: {str(e)}'
        }), 404

def init_db():
    with app.app_context():
        db.create_all()
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@ciet.com',
                is_admin=True
            )
            admin.set_password('admin123')  # Change this in production
            db.session.add(admin)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True) 