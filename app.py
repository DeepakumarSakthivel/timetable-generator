from flask import Flask, request, jsonify, render_template, send_file
from timetableapp.timetable_generator import TimetableGenerator
from datetime import datetime, timedelta
import os
from timetableapp.models import db, ClassInfo, Subject, Faculty, Timetable, TimetableEntry
import random
from collections import defaultdict
from timetableapp.timetable_logic import TimetableLogic
import logging
from timetableapp.admin import init_admin
import csv
import io
import pandas as pd
from timetableapp.populate_demo_data import populate as populate_demo_data

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///timetable.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Initialize admin panel
init_admin(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_timetable():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
            
        logger.info('Received timetable generation request')
        logger.debug(f'Request data: {data}')
        
        sections = data.get('sections', [])
        if not sections:
            return jsonify({'success': False, 'message': 'No sections provided'}), 400
            
        subjects = []
        for subject in data.get('subjects', []):
            if not subject.get('name'):
                return jsonify({'success': False, 'message': 'Subject name is required'}), 400
            if not subject.get('credits'):
                return jsonify({'success': False, 'message': 'Subject credits are required'}), 400
                
            is_lab = subject.get('is_lab', False)
            if isinstance(is_lab, str):
                is_lab = is_lab.lower() == 'true' or is_lab == 'on'
            embedded = subject.get('embedded', False)
            if isinstance(embedded, str):
                embedded = embedded.lower() == 'true' or embedded == 'on'
            subjects.append({
                'name': subject['name'],
                'credits': int(subject['credits']),
                'faculty': subject.get('faculty', ''),
                'is_lab': is_lab,
                'embedded': embedded
            })
            
        if not subjects:
            return jsonify({'success': False, 'message': 'No subjects provided'}), 400

        logger.info(f'Processing timetable for sections: {sections}')
        logic = TimetableLogic(sections, subjects)
        timetables = logic.generate()
        
        # Generate PDF
        try:
            generator = TimetableGenerator()
            for section in sections:
                generator.add_section(section)
            for subject in subjects:
                generator.add_subject(
                    name=subject['name'],
                    credits=subject['credits'],
                    faculty=subject['faculty'],
                    is_lab=subject['is_lab'],
                    embedded=subject['embedded']
                )
            generator.generate_timetable()
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pdf_filename = f'timetable_{timestamp}.pdf'
            pdf_path = os.path.join('static', 'pdfs', pdf_filename)
            os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
            
            faculty_subjects = {f"{subject.get('code', '')} - {subject['name']}": subject.get('faculty', '') 
                              for subject in data.get('subjects', [])}
            
            pdf_success = generator.generate_pdf(
                pdf_path,
                department=data.get('department', ''),
                year=data.get('year', ''),
                faculty_subjects=faculty_subjects,
                dates=None,
                semester=data.get('semester', ''),
                class_name=', '.join(sections),
                batch=data.get('batch', ''),
                hall_no=', '.join(data.get('halls', [])),
                subject_mapping=[
                    {
                        'code': subject.get('code', ''),
                        'title': subject['name'],
                        'faculty': subject.get('faculty', '')
                    } for subject in data.get('subjects', [])
                ],
                wef=data.get('wef', '')
            )
            
            if not pdf_success:
                logger.error('Failed to generate PDF')
                return jsonify({
                    'success': False,
                    'message': 'Failed to generate PDF',
                    'timetables': timetables
                }), 500
                
            logger.info('Successfully generated timetable and PDF')
            return jsonify({
                'success': True,
                'timetables': timetables,
                'faculty_subjects': faculty_subjects,
                'pdf_url': f'/static/pdfs/{pdf_filename}'
            })
            
        except Exception as pdf_error:
            logger.error(f'Error generating PDF: {str(pdf_error)}')
            return jsonify({
                'success': False,
                'message': f'Error generating PDF: {str(pdf_error)}',
                'timetables': timetables
            }), 500
            
    except Exception as e:
        logger.error(f'Error in generate_timetable: {str(e)}')
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/generate_from_db', methods=['POST'])
def generate_from_db():
    try:
        data = request.get_json()
        class_id = data.get('class_id')
        if not class_id:
            return jsonify({'success': False, 'message': 'class_id is required'}), 400
        class_info = ClassInfo.query.get(class_id)
        if not class_info:
            return jsonify({'success': False, 'message': 'Class not found'}), 404
        subjects = Subject.query.filter_by(class_id=class_id).all()
        generator = TimetableGenerator()
        generator.add_section(class_info.class_name)
        for subj in subjects:
            faculty = Faculty.query.get(subj.faculty_id)
            generator.add_subject(
                name=subj.course_title,
                code=subj.course_code,
                credits=subj.credits,
                faculty=faculty.name if faculty else '',
                is_lab=subj.is_lab,
                embedded=subj.embedded
            )
        generator.generate_timetable()

        # --- Save generated timetable to database ---
        # Create a new Timetable record
        new_timetable = Timetable(
            class_id=class_id,
            # Assuming a simple versioning, you might want more sophisticated logic
            version= (db.session.query(db.func.max(Timetable.version)).filter_by(class_id=class_id).scalar() or 0) + 1,
            is_active=True, # Set this as the active timetable for the class
            # created_by should be added if user context is available, skipping for now
        )
        db.session.add(new_timetable)
        db.session.flush() # Assigns an ID to new_timetable

        # Iterate through generated timetable and save entries
        # Assuming generator.timetables is {section_name: [[day1_period1, day2_period1, ...], ...]}
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"] # Assuming 5 days
        break_slots = [2, 5] # Assuming these are consistent with generator

        for section, timetable_grid in generator.timetables.items():
            # Assuming only one section is generated per class_id for now based on current logic
            if section != class_info.class_name:
                logger.warning(f"Generated timetable for unexpected section: {section}")
                continue

            for period_idx, day_entries in enumerate(timetable_grid):
                if period_idx in break_slots:
                    continue # Skip break slots

                for day_idx, entry_content in enumerate(day_entries):
                    if entry_content and entry_content != "-": # Check if the slot is not empty or break filler
                        # entry_content format is expected to be "Course Code - Course Title (Faculty Name)" or "Course Title (Faculty Name)"
                        # or potentially just "Subject Name" for non-lab.

                        subject = None
                        faculty = None
                        subject_name_from_generator = ""
                        faculty_name_from_generator = ""

                        # Attempt to split by '(' to get potential faculty part
                        parts = entry_content.split("(")
                        subject_part_raw = parts[0].strip()
                        if len(parts) > 1:
                            faculty_name_from_generator = parts[1].replace(")", "").strip()

                        # --- Attempt to find Subject ---
                        # Clean up subject name: remove '(LAB)' if present and strip spaces
                        subject_name_cleaned = subject_part_raw.replace(' (LAB)', '').strip()

                        # Try to find the subject by the cleaned name (most common case)
                        subject = Subject.query.filter_by(course_title=subject_name_cleaned).first()

                        # Fallback: If not found by cleaned name, try the raw subject part (might include code or other variations)
                        if not subject and subject_part_raw != subject_name_cleaned:
                             subject = Subject.query.filter_by(course_title=subject_part_raw).first()

                        # --- Attempt to find Faculty ---
                        # If a faculty name was extracted, try to find the faculty record
                        if faculty_name_from_generator:
                            faculty = Faculty.query.filter_by(name=faculty_name_from_generator).first()

                        # --- Save Entry if Subject and Faculty Found ---
                        # Only save the entry if we successfully found both a subject and a faculty
                        if subject and faculty:
                             # Check for existing entry to avoid duplicates on re-runs if not cleaning up old timetables
                             existing_entry = TimetableEntry.query.filter_by(
                                 timetable_id=new_timetable.id,
                                 day=days[day_idx],
                                 period=period_idx + 1 # periods are 1-indexed in DB model
                             ).first()

                             if not existing_entry:
                                 timetable_entry = TimetableEntry(
                                     timetable_id=new_timetable.id,
                                     subject_id=subject.id,
                                     faculty_id=faculty.id,
                                     period=period_idx + 1, # DB periods are 1-indexed
                                     day=days[day_idx]
                                 )
                                 db.session.add(timetable_entry)
                             else:
                                 logger.warning(f"Skipping duplicate timetable entry for timetable_id={new_timetable.id}, day={days[day_idx]}, period={period_idx + 1}.")

                        else:
                            # Log more specifically why the entry is skipped
                            reason = []
                            if not subject:
                                reason.append(f"Subject '{subject_name_cleaned}' (or original) not found")
                            if not faculty:
                                reason.append(f"Faculty '{faculty_name_from_generator}' not found or not specified")
                            logger.warning(f"Skipping entry '{entry_content}': {', '.join(reason)}.")


        db.session.commit()
        logger.info(f"Timetable for class_id {class_id} saved successfully with ID {new_timetable.id}")
        # --- End Save generated timetable to database ---


        # Prepare faculty-subject mapping
        faculty_subjects = {}
        for subj in subjects:
            faculty = Faculty.query.get(subj.faculty_id)
            key = f"{subj.course_code} - {subj.course_title}"
            faculty_subjects[key] = faculty.name if faculty else ''
        # Generate PDF
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f'timetable_{timestamp}.pdf'
        pdf_path = os.path.join('static', 'pdfs', pdf_filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
        pdf_success = generator.generate_pdf(
            pdf_path,
            department=class_info.class_name,
            year=class_info.semester,
            faculty_subjects=faculty_subjects,
            dates=None,
            semester=class_info.semester,
            class_name=class_info.class_name,
            batch=class_info.batch,
            hall_no=class_info.hall_no,
            subject_mapping=[
                {
                    'code': subj.course_code,
                    'title': subj.course_title,
                    'faculty': Faculty.query.get(subj.faculty_id).name if Faculty.query.get(subj.faculty_id) else ''
                } for subj in subjects
            ],
            wef=class_info.effect_from
        )
        if pdf_success:
            return jsonify({
                'success': True,
                'message': 'Timetable generated successfully',
                'pdf_url': f'/static/pdfs/{pdf_filename}',
                'timetables': generator.timetables,
                'faculty_subjects': faculty_subjects
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to generate timetable PDF'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/export/csv/<table_name>')
def export_csv(table_name):
    try:
        if table_name == 'subjects':
            query = Subject.query.all()
            data = [{
                'id': item.id,
                'class_id': item.class_id,
                'course_code': item.course_code,
                'course_title': item.course_title,
                'faculty_id': item.faculty_id,
                'credits': item.credits,
                'is_lab': item.is_lab,
                'embedded': item.embedded
            } for item in query]
        elif table_name == 'faculty':
            query = Faculty.query.all()
            data = [{
                'id': item.id,
                'name': item.name,
                'email': item.email,
                'department': item.department,
                'max_hours_per_day': item.max_hours_per_day
            } for item in query]
        elif table_name == 'classes':
            query = ClassInfo.query.all()
            data = [{
                'id': item.id,
                'class_name': item.class_name,
                'semester': item.semester,
                'batch': item.batch,
                'hall_no': item.hall_no,
                'effect_from': item.effect_from.strftime('%Y-%m-%d')
            } for item in query]
        else:
            return jsonify({'error': 'Invalid table name'}), 400

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        # Create the response
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'{table_name}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/import/csv/<table_name>', methods=['POST'])
def import_csv(table_name):
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if not file.filename.endswith('.csv'):
            return jsonify({'error': 'File must be a CSV'}), 400

        # Read CSV file
        df = pd.read_csv(file)
        
        if table_name == 'subjects':
            for _, row in df.iterrows():
                subject = Subject(
                    class_id=row['class_id'],
                    course_code=row['course_code'],
                    course_title=row['course_title'],
                    faculty_id=row['faculty_id'],
                    credits=row['credits'],
                    is_lab=row['is_lab'],
                    embedded=row['embedded']
                )
                db.session.add(subject)
        elif table_name == 'faculty':
            for _, row in df.iterrows():
                faculty = Faculty(
                    name=row['name'],
                    email=row['email'],
                    department=row['department'],
                    max_hours_per_day=row['max_hours_per_day']
                )
                db.session.add(faculty)
        elif table_name == 'classes':
            for _, row in df.iterrows():
                class_info = ClassInfo(
                    class_name=row['class_name'],
                    semester=row['semester'],
                    batch=row['batch'],
                    hall_no=row['hall_no'],
                    effect_from=datetime.strptime(row['effect_from'], '%Y-%m-%d').date()
                )
                db.session.add(class_info)
        else:
            return jsonify({'error': 'Invalid table name'}), 400

        db.session.commit()
        return jsonify({'message': f'Successfully imported {table_name} data'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@app.cli.command('populate-db')
def populate_db_command():
    "Populate the database with demo data."
    populate_demo_data(app, db)
    print('Database populated with demo data.')

# Admin panel available at http://127.0.0.1:5000/admin

import os

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)