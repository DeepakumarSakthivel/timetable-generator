from flask_admin.contrib.sqla import ModelView
from flask_admin import Admin, BaseView, expose
from flask_login import current_user
from timetableapp.models import db, User, ClassInfo, Subject, Faculty, Timetable, TimetableEntry
from datetime import datetime

class SecureModelView(ModelView):
    can_export = True
    can_view_details = True
    page_size = 50
    def is_accessible(self):
        return True  # TEMP: Allow all users for debugging

class UserAdmin(SecureModelView):
    column_exclude_list = ['password_hash']
    column_searchable_list = ['username', 'email']
    column_filters = ['is_admin', 'created_at']
    form_excluded_columns = ['password_hash']
    
    def on_model_change(self, form, model, is_created):
        if is_created:
            model.set_password(form.password.data)

class ClassInfoAdmin(SecureModelView):
    column_searchable_list = ['class_name', 'semester', 'batch']
    column_filters = ['semester', 'batch', 'created_at']
    form_columns = ['class_name', 'semester', 'batch', 'hall_no', 'effect_from']
    column_details_list = ['class_name', 'semester', 'batch', 'hall_no', 'effect_from']

class SubjectAdmin(SecureModelView):
    column_searchable_list = ['course_code', 'course_title']
    column_filters = ['is_lab', 'embedded', 'credits', 'created_at']
    form_columns = ['class_info', 'course_code', 'course_title', 'faculty', 'credits', 'is_lab', 'embedded']
    column_details_list = ['class_info', 'course_code', 'course_title', 'faculty', 'credits', 'is_lab', 'embedded']
    column_list = ['course_code', 'course_title', 'faculty', 'class_info', 'credits', 'is_lab', 'embedded']

class FacultyAdmin(SecureModelView):
    column_searchable_list = ['name', 'email', 'department']
    column_filters = ['department', 'created_at']
    form_columns = ['name', 'email', 'department', 'max_hours_per_day']
    column_details_list = ['name', 'email', 'department', 'max_hours_per_day']

class TimetableAdmin(SecureModelView):
    column_searchable_list = ['class_id']
    column_filters = ['is_active', 'created_at']
    form_columns = ['class_info', 'version', 'is_active']
    column_details_list = ['class_info', 'version', 'is_active']

class TimetableEntryAdmin(SecureModelView):
    column_searchable_list = ['timetable_id', 'subject_id', 'faculty_id']
    column_filters = ['day', 'period', 'created_at']
    form_columns = ['timetable', 'subject', 'faculty', 'period', 'day']
    column_details_list = ['timetable', 'subject', 'faculty', 'period', 'day']

class DashboardView(BaseView):
    @expose('/')
    def index(self):
        stats = {
            'total_classes': ClassInfo.query.count(),
            'total_subjects': Subject.query.count(),
            'total_faculty': Faculty.query.count(),
            'active_timetables': Timetable.query.filter_by(is_active=True).count()
        }
        return self.render('admin/dashboard.html', stats=stats)

def init_admin(app):
    admin = Admin(app, name='CIET Timetable Admin', template_mode='bootstrap4')
    # Register CRUD views first
    admin.add_view(UserAdmin(User, db.session))
    admin.add_view(ClassInfoAdmin(ClassInfo, db.session))
    admin.add_view(SubjectAdmin(Subject, db.session))
    admin.add_view(FacultyAdmin(Faculty, db.session))
    admin.add_view(TimetableAdmin(Timetable, db.session))
    admin.add_view(TimetableEntryAdmin(TimetableEntry, db.session))
    # Add dashboard as a separate menu item
    admin.add_view(DashboardView(name='Dashboard')) 