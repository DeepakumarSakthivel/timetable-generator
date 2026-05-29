import random
from collections import defaultdict
from fpdf import FPDF # type: ignore
import datetime
import os
from .timetable_logic import TimetableLogic

# Helper function to get integer input

def get_int(prompt, min_val=1, max_val=100):
    while True:
        try:
            val = int(input(prompt))
            if min_val <= val <= max_val:
                return val
            else:
                print(f"Enter a value between {min_val} and {max_val}.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def get_str(prompt):
    return input(prompt).strip()

def get_choice(prompt, choices):
    while True:
        val = input(f"{prompt} ({'/'.join(choices)}): ").strip().lower()
        if val in choices:
            return val
        print(f"Please enter one of: {', '.join(choices)}")

class TimetableGenerator:
    def __init__(self):
        self.sections = []
        self.faculty = []
        self.subjects = []
        self.timetables = {}
        self.break_slots = [2, 5]  # Break slots (0-based index)
    
    def add_section(self, name):
        self.sections.append(name)
    
    def add_faculty(self, name, subjects):
        self.faculty.append({
            "name": name,
            "subjects": subjects
        })
    
    def add_subject(self, name, credits, faculty, is_lab=False, embedded=False, code=None):
        self.subjects.append({
            "name": name,
            "credits": credits,
            "faculty": faculty,
            "is_lab": is_lab,
            "embedded": embedded,
            "code": code
        })

    def generate_timetable(self, num_days=5, num_sessions=9):
        logic = TimetableLogic(self.sections, self.subjects)
        self.timetables = logic.generate()
        # Step 4: Guarantee 9x5 grid for every section
        for section in self.sections:
            # Ensure 9 sessions
            while len(self.timetables[section]) < 9:
                self.timetables[section].append(["-"] * 5)
            # Ensure each session has 5 days
            for session in range(9):
                if len(self.timetables[section][session]) < 5:
                    self.timetables[section][session] += ["-"] * (5 - len(self.timetables[section][session]))
                elif len(self.timetables[section][session]) > 5:
                    self.timetables[section][session] = self.timetables[section][session][:5]

    def generate_pdf(self, filename="timetable.pdf", department=None, year=None, faculty_subjects=None, dates=None, semester=None, class_name=None, batch=None, hall_no=None, subject_mapping=None, wef=None):
        try:
            pdf = FPDF(orientation='L', unit='mm', format='A4')
            session_labels = [
                ("Session I", "9:00AM", "9:50AM"),
                ("Session II", "9:50AM", "10:40AM"),
                ("TEABREAK", "10:40AM", "11:00AM"),
                ("Session III", "11:00AM", "11:50AM"),
                ("Session IV", "11:50AM", "12:40PM"),
                ("LUNCH", "12:40PM", "1:45PM"),
                ("Session V", "1:45PM", "2:30PM"),
                ("Session VI", "2:30PM", "3:15PM"),
                ("Session VII", "3:15PM", "4:00PM")
            ]
            break_slots = [2, 5]
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
            # Reduce the width of the 'Day' column to 15mm, keep session columns at 27.5mm
            col_widths = [15] + [27.5] * 8  # 15mm for Day, 27.5mm for each session

            for section in self.sections:
                pdf.add_page()
                # --- Meta Info Header (single row) ---
                pdf.set_font("Helvetica", "B", 10) # Reduced font for meta to save space
                pdf.cell(50, 7, f"SEMESTER: {semester if semester else ''}", border=0)
                pdf.cell(50, 7, f"DEPARTMENT: {department if department else ''}", border=0)
                pdf.cell(50, 7, f"SECTION: {section}", border=0)
                pdf.cell(50, 7, f"W.E.F: {wef if wef else ''}", border=0)
                pdf.cell(50, 7, f"BATCH: {batch if batch else ''}", border=0)
                pdf.cell(40, 7, f"HALLNO: {hall_no if hall_no else ''}", border=0)
                pdf.ln(10) # Reduced ln space

                # --- Timetable Table ---
                header_cell_height = 6 # Height for session and time rows
                day_header_col_width = col_widths[0]
                session_col_width = col_widths[1]

                pdf.set_font("Helvetica", "B", 8) # Font size for headers
                pdf.cell(day_header_col_width, header_cell_height * 2, "Day", 1, 0, 'C') # Changed header to 'Day'

                current_x = pdf.get_x()
                current_y = pdf.get_y()

                for i, (label, _, _) in enumerate(session_labels):
                    pdf.set_xy(current_x + (i * session_col_width), current_y)
                    if i in break_slots:
                        pdf.set_fill_color(220, 220, 220)
                        pdf.cell(session_col_width, header_cell_height, label, 1, 0, 'C', fill=True)
                    else:
                        pdf.cell(session_col_width, header_cell_height, label, 1, 0, 'C')
                pdf.ln(header_cell_height)

                pdf.set_xy(current_x, current_y + header_cell_height)
                for i, (_, start, end) in enumerate(session_labels):
                    time_text = f"{start} - {end}"
                    if i in break_slots:
                        pdf.set_fill_color(220, 220, 220)
                        pdf.cell(session_col_width, header_cell_height, time_text, 1, 0, 'C', fill=True)
                    else:
                        pdf.cell(session_col_width, header_cell_height, time_text, 1, 0, 'C')
                pdf.ln(header_cell_height)
                
                # --- Timetable Rows (Data) ---
                pdf.set_font("Helvetica", "", 8) # Reduced font for content
                timetable_row_height = 10 # Increased height for timetable content cells

                for day_idx, day in enumerate(days):
                    pdf.cell(day_header_col_width, timetable_row_height, day, 1, 0, 'C')
                    s = 0
                    while s < len(session_labels):
                        actual_col_width = session_col_width
                        if s in break_slots:
                            pdf.set_fill_color(220, 220, 220)
                            pdf.cell(actual_col_width, timetable_row_height, session_labels[s][0], 1, 0, 'C', fill=True)
                            s += 1
                        else:
                            cell_content = self.timetables[section][s][day_idx] if s < len(self.timetables[section]) and day_idx < len(self.timetables[section][s]) else "-"
                            subj_code = ""
                            for subj in self.subjects:
                                if subj["name"] == cell_content or subj["name"] in str(cell_content):
                                    subj_code = subj.get("code", "")
                                    break
                            display_text = f"{subj_code}" if subj_code else (cell_content if cell_content else "-")

                            # Check if the current cell content is the start of a span for a lab/embedded subject
                            is_spanning_subject = False
                            if cell_content and ("LAB" in str(cell_content).upper() or (subj_code and "LAB" in subj_code.upper())):
                                # Determine the span length for this subject block
                                lab_span = 1
                                # Iterate through subsequent sessions on the same day
                                for k in range(s + 1, len(session_labels)):
                                    # Stop spanning if we hit a break slot or a different subject/empty cell
                                    next_cell_content = self.timetables[section][k][day_idx] if k < len(self.timetables[section]) and day_idx < len(self.timetables[section][k]) else "-"
                                    if k in break_slots or next_cell_content != cell_content:
                                        break
                                    lab_span += 1
                                   
                                if lab_span > 1: # Only span if the subject continues into the next session(s)
                                    is_spanning_subject = True
                                    actual_col_width = session_col_width * lab_span
                                   
                                    # Store the current position before drawing the multi-cell
                                    start_x = pdf.get_x()
                                    start_y = pdf.get_y()

                                    # Draw the multi-cell for the spanned subject
                                    pdf.multi_cell(actual_col_width, timetable_row_height, display_text, 1, 'C')

                                    # Reset the position to continue drawing the row after the spanned cell
                                    pdf.set_xy(start_x + actual_col_width, start_y) # Use set_xy to move to the right of the multi-cell

                                    s += lab_span # Advance session index by the span length
                                else: # Subject does not span, treat as a regular cell
                                    pdf.cell(actual_col_width, timetable_row_height, display_text, 1, 0, 'C')
                                    s += 1
                            else: # Not a spanning lab/embedded subject
                                pdf.cell(actual_col_width, timetable_row_height, display_text, 1, 0, 'C')
                                s += 1
                    pdf.ln(timetable_row_height)
                pdf.ln(3) # Space after timetable grid

                # --- Subject & Faculty Mapping Table for this section ---
                section_subjects = [subj for subj in (subject_mapping or []) if subj.get('section', section) == section or subj.get('section') is None]
                if section_subjects:
                    pdf.ln(2) # Reduced space before subject mapping
                    pdf.set_font("Helvetica", "B", 10)
                    pdf.cell(0, 10, "SUBJECT & FACULTY DETAILS", 0, 1, 'C')
                    pdf.set_font("Helvetica", "B", 9)
                    mapping_header_height = 7
                    mapping_row_height = 8
                    pdf.cell(15, mapping_header_height, "S.No", 1, 0, 'C')
                    pdf.cell(30, mapping_header_height, "COURSE CODE", 1, 0, 'C')
                    pdf.cell(75, mapping_header_height, "COURSE TITLE", 1, 0, 'C')
                    pdf.cell(70, mapping_header_height, "FACULTY NAME", 1, 1, 'C')
                    pdf.set_font("Helvetica", "", 8)
                    for idx, row in enumerate(section_subjects, 1):
                        pdf.cell(15, mapping_row_height, str(idx), 1, 0, 'C')
                        pdf.cell(30, mapping_row_height, row.get('code', ''), 1, 0, 'C')
                        pdf.cell(75, mapping_row_height, row.get('title', ''), 1, 0, 'C')
                        pdf.cell(70, mapping_row_height, row.get('faculty', ''), 1, 1, 'C')

            pdf.output(filename)
            print(f"PDF generated successfully at: {os.path.abspath(filename)}")
            return True
        except Exception as e:
            print(f"Error generating PDF: {str(e)}")
            return False

def main():
    generator = TimetableGenerator()
    
    # Add sections
    generator.add_section("CSE A")
    generator.add_section("CSE B")
    
    # Add faculty
    generator.add_faculty("Dr. Smith", ["Data Structures", "Algorithms"])
    generator.add_faculty("Prof. Johnson", ["Database Systems", "Web Development"])
    generator.add_faculty("Dr. Williams", ["Computer Networks", "Operating Systems"])
    
    # Add subjects
    generator.add_subject("Data Structures", 3, "Dr. Smith", is_lab=True, embedded=True)
    generator.add_subject("Database Systems", 3, "Prof. Johnson", is_lab=True, embedded=False)
    generator.add_subject("Computer Networks", 3, "Dr. Williams", is_lab=True, embedded=True)
    generator.add_subject("Algorithms", 3, "Dr. Smith")
    generator.add_subject("Web Development", 3, "Prof. Johnson")
    generator.add_subject("Operating Systems", 3, "Dr. Williams")
    
    # Generate timetables
    generator.generate_timetable()
    
    # Generate PDF
    if generator.generate_pdf():
        print("Timetable generated successfully!")
    else:
        print("Failed to generate timetable PDF.")

if __name__ == "__main__":
    main() 