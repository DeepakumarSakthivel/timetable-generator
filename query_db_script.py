from app import app, db
from timetableapp.models import Timetable, TimetableEntry, ClassInfo

with app.app_context():
    print('--- ClassInfo Data ---')
    classes = ClassInfo.query.all()
    if classes:
        for c in classes:
            print(f'ID: {c.id}, Class Name: {c.class_name}, Semester: {c.semester}, Batch: {c.batch}, Hall No: {c.hall_no}, Effect From: {c.effect_from}')
    else:
        print('No ClassInfo records found.')

    print('\n--- Timetable Data ---')
    timetables = Timetable.query.all()
    if timetables:
        for t in timetables:
            print(f'ID: {t.id}, Class ID: {t.class_id}, Version: {t.version}, Active: {t.is_active}, Created At: {t.created_at}')
    else:
        print('No Timetable records found.')

    print('\n--- TimetableEntry Data ---')
    entries = TimetableEntry.query.all()
    if entries:
        for e in entries:
            print(f'ID: {e.id}, Timetable ID: {e.timetable_id}, Subject ID: {e.subject_id}, Faculty ID: {e.faculty_id}, Day: {e.day}, Period: {e.period}, Created At: {e.created_at}')
    else:
        print('No TimetableEntry records found.') 