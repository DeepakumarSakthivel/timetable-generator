import random
import math
from collections import defaultdict

class TimetableLogic:
    def __init__(self, sections, subjects):
        self.sections = sections
        # Automatically handle both per-section and flat subject list input
        if isinstance(subjects, dict):
            self.subjects_per_section = subjects
        else:
            # Flat list: use same subjects for all sections
            self.subjects_per_section = {section: subjects for section in sections}
        self.timetables = {}
        self.break_slots = [2, 5]  # 0-based index for TEABREAK and LUNCH
        self.num_days = 5
        self.num_sessions = 9
        self.global_faculty_schedule = defaultdict(lambda: defaultdict(set))

    def generate(self):
        # Teaching sessions per day (excluding breaks/lunch)
        teaching_sessions_per_day = 7
        total_teaching_slots = teaching_sessions_per_day * self.num_days  # 7 x 5 = 35
        for section in self.sections:
            subjects = self.subjects_per_section[section]
            total_credits = sum(s["credits"] for s in subjects)
            if total_credits < total_teaching_slots:
                print(f"WARNING: Section {section} - Total credits ({total_credits}) is less than total teaching slots ({total_teaching_slots}). There will be {total_teaching_slots - total_credits} free sessions.")
            elif total_credits > total_teaching_slots:
                print(f"ERROR: Section {section} - Total credits ({total_credits}) exceeds total teaching slots ({total_teaching_slots}). Timetable cannot be generated without over-allocating subjects.")
            else:
                print(f"INFO: Section {section} - Total credits exactly match total teaching slots. No free sessions will appear.")

        # Initialize timetable grid
        for section in self.sections:
            self.timetables[section] = [[None for _ in range(self.num_days)] for _ in range(self.num_sessions)]
            for day in range(self.num_days):
                for break_slot in self.break_slots:
                    self.timetables[section][break_slot][day] = "BREAK/LUNCH"

        # Step 1: Allocate labs and embedded components as blocks
        for section in self.sections:
            subjects = self.subjects_per_section[section]
            
            # Separate subjects into categories
            pure_lab_subjects = [s for s in subjects if s["is_lab"] and not s.get("embedded", False)]
            lab_embedded_subjects = [s for s in subjects if s["is_lab"] and s.get("embedded", False)]
            embedded_only_subjects = [s for s in subjects if not s["is_lab"] and s.get("embedded", False)]

            # Process Pure Lab Subjects (Block Size 3)
            print(f"DEBUG: Section {section} - Attempting to place Pure Lab blocks: {[s['name'] for s in pure_lab_subjects]}")
            random.shuffle(pure_lab_subjects) # Shuffle for fairness
            for subject in pure_lab_subjects:
                block_size = 3
                blocks_needed = math.ceil(subject["credits"] / block_size)
                lab_label = f"{subject['name']} (LAB)"

                print(f"DEBUG:    Processing Pure Lab subject: {subject['name']}, Credits: {subject['credits']}, Block Size: {block_size}, Blocks Needed: {blocks_needed}. Generated Label: {lab_label}")

                blocks_placed_count = 0
                # Attempt contiguous placement for Pure Labs
                for _ in range(blocks_needed):
                    placed = False
                    random.shuffle(list(range(self.num_days))) # Shuffle days
                    for day in range(self.num_days):
                        # Check if any lab or embedded subject is already placed on this day
                        is_lab_or_embedded_on_day = any(
                            self.timetables[section][session][day] is not None and any(
                                self.timetables[section][session][day] == s["name"] or self.timetables[section][session][day] == f"{s['name']} (LAB)"
                                for s in pure_lab_subjects + lab_embedded_subjects + embedded_only_subjects
                            ) for session in range(self.num_sessions) if session not in self.break_slots
                        )
                        if is_lab_or_embedded_on_day:
                            # print(f"DEBUG:    Skipping day {day} for {subject['name']} (Pure Lab) due to existing lab/embedded on this day.")
                            continue # Skip this day if a lab or embedded is already placed

                        sessions_placed_today = sum(1 for session in range(self.num_sessions) if self.timetables[section][session][day] == lab_label)
                        if sessions_placed_today >= block_size:
                            continue
                        
                        possible_starts = [session for session in range(self.num_sessions) if session not in self.break_slots]
                        random.shuffle(possible_starts)

                        for start in possible_starts:
                            block_indices = list(range(start, start + block_size))
                            if any(idx >= self.num_sessions or idx in self.break_slots for idx in block_indices):
                                continue

                            clash = False
                            for offset in range(block_size):
                                idx = start + offset
                                if self.timetables[section][idx][day] is not None:
                                    clash = True
                                    break
                                for other_section in self.sections:
                                    if subject["faculty"] in self.global_faculty_schedule[day][idx]:
                                        clash = True
                                        break
                                if clash:
                                    break

                            if not clash:
                                print(f"DEBUG:    Placing block of {lab_label} starting at session {start}, day {day}.")
                                for offset in range(block_size):
                                    idx = start + offset
                                    self.timetables[section][idx][day] = lab_label
                                    self.global_faculty_schedule[day][idx].add(subject["faculty"])
                                blocks_placed_count += 1
                                placed = True
                                break
                        if placed:
                            break

                # After contiguous placement, attempt morning + session 0 fallback for remaining Pure Lab blocks
                remaining_blocks = blocks_needed - (blocks_placed_count // block_size if block_size > 0 else 0)
                if remaining_blocks > 0:
                    print(f"WARNING: Could not place all required contiguous blocks for Pure Lab subject {subject['name']} in section {section}. {remaining_blocks} blocks still unplaced. Attempting morning paired placement.")

                    # Try placing ONE remaining block in the morning + session 0 pair
                    if remaining_blocks >= 1:
                        print(f"DEBUG:    Attempting morning + session 0 placement for one block of {subject['name']}.")
                        placed_in_morning_pair = False
                        random.shuffle(list(range(self.num_days))) # Shuffle days
                        for day in range(self.num_days):
                            # Check if any lab or embedded subject is already placed in a morning session (0-4, excluding breaks) on this day
                            existing_subject_part_in_morning = any(
                                self.timetables[section][session][day] is not None and any(
                                     self.timetables[section][session][day] == s["name"] or self.timetables[section][session][day] == f"{s['name']} (LAB)"
                                     for s in pure_lab_subjects + lab_embedded_subjects + embedded_only_subjects
                                ) for session in [0, 1, 3, 4] if session not in self.break_slots
                            )
                            if existing_subject_part_in_morning:
                                print(f"DEBUG:    Skipping day {day} for {subject['name']} morning pair due to existing subject part in morning.")
                                continue

                            # Check if session 0 already has content, if so, skip this day
                            if self.timetables[section][0][day] is not None and self.timetables[section][0][day] != subject["name"]:
                                continue

                            session_0_already_has_subject = self.timetables[section][0][day] == subject["name"]
                            morning_start_sessions = [1, 3, 4]
                            random.shuffle(morning_start_sessions)

                            for start in morning_start_sessions:
                                if start + block_size > 5:
                                    continue
                                block_indices = list(range(start, start + block_size))
                                if any(idx in self.break_slots for idx in block_indices):
                                    continue

                                clash = False
                                if not session_0_already_has_subject and subject["faculty"] in self.global_faculty_schedule[day][0]:
                                    clash = True

                                if not clash:
                                    for offset in range(block_size):
                                        idx = start + offset
                                        if self.timetables[section][idx][day] is not None:
                                            clash = True
                                            break
                                        for other_section in self.sections:
                                            if subject["faculty"] in self.global_faculty_schedule[day][idx]:
                                                clash = True
                                                break
                                        if clash:
                                            break

                                if not clash:
                                    if not session_0_already_has_subject:
                                        print(f"DEBUG:    Placing {subject['name']} (theory part) at session 0, day {day} for morning pair.")
                                        self.timetables[section][0][day] = subject["name"]
                                        self.global_faculty_schedule[day][0].add(subject["faculty"])

                                    print(f"DEBUG:    Placing block of {lab_label} starting at session {start}, day {day} (morning pair). Duration: {block_size}")
                                    for offset in range(block_size):
                                        idx = start + offset
                                        self.timetables[section][idx][day] = lab_label
                                        self.global_faculty_schedule[day][idx].add(subject["faculty"])
                                    placed_in_morning_pair = True
                                    remaining_blocks -= 1
                                    blocks_placed_count += block_size
                                    break
                            if placed_in_morning_pair:
                                break

                # Remaining blocks for Pure Labs (if any) are left as '-'
                if remaining_blocks > 0:
                    print(f"INFO: {remaining_blocks} blocks for Pure Lab subject {subject['name']} in section {section} could not be placed and will result in free slots ('-').")

            # Process Lab + Embedded Subjects (Block Size 2)
            print(f"DEBUG: Section {section} - Attempting to place Lab + Embedded blocks: {[s['name'] for s in lab_embedded_subjects]}")
            random.shuffle(lab_embedded_subjects) # Shuffle for fairness
            for subject in lab_embedded_subjects:
                block_size = 2
                blocks_needed = math.ceil(subject["credits"] / block_size)
                lab_label = f"{subject['name']} (LAB)" # Label includes (LAB) as it has a lab component

                print(f"DEBUG:    Processing Lab + Embedded subject: {subject['name']}, Credits: {subject['credits']}, Block Size: {block_size}, Blocks Needed: {blocks_needed}. Generated Label: {lab_label}")

                blocks_placed_count = 0
                # Attempt contiguous placement for Lab + Embedded
                for _ in range(blocks_needed):
                    placed = False
                    random.shuffle(list(range(self.num_days))) # Shuffle days
                    for day in range(self.num_days):
                        # Check if any lab or embedded subject is already placed on this day
                        is_lab_or_embedded_on_day = any(
                            self.timetables[section][session][day] is not None and any(
                                self.timetables[section][session][day] == s["name"] or self.timetables[section][session][day] == f"{s['name']} (LAB)"
                                for s in pure_lab_subjects + lab_embedded_subjects + embedded_only_subjects
                            ) for session in range(self.num_sessions) if session not in self.break_slots
                        )
                        if is_lab_or_embedded_on_day:
                            # print(f"DEBUG:    Skipping day {day} for {subject['name']} (Lab+Embedded) due to existing lab/embedded on this day.")
                            continue # Skip this day if a lab or embedded is already placed

                        sessions_placed_today = sum(1 for session in range(self.num_sessions) if self.timetables[section][session][day] == lab_label)
                        if sessions_placed_today >= block_size:
                            continue

                        possible_starts = [session for session in range(self.num_sessions) if session not in self.break_slots]
                        random.shuffle(possible_starts)

                        for start in possible_starts:
                            block_indices = list(range(start, start + block_size))
                            if any(idx >= self.num_sessions or idx in self.break_slots for idx in block_indices):
                                continue

                            clash = False
                            for offset in range(block_size):
                                idx = start + offset
                                if self.timetables[section][idx][day] is not None:
                                    clash = True
                                    break
                                for other_section in self.sections:
                                    if subject["faculty"] in self.global_faculty_schedule[day][idx]:
                                        clash = True
                                        break
                                if clash:
                                    break

                            if not clash:
                                print(f"DEBUG:    Placing block of {lab_label} starting at session {start}, day {day}.")
                                for offset in range(block_size):
                                    idx = start + offset
                                    self.timetables[section][idx][day] = lab_label
                                    self.global_faculty_schedule[day][idx].add(subject["faculty"])
                                blocks_placed_count += 1
                                placed = True
                                break
                        if placed:
                            break

                # Remaining blocks for Lab + Embedded (if any) are left as '-'
                remaining_blocks = blocks_needed - (blocks_placed_count // block_size if block_size > 0 else 0)
                if remaining_blocks > 0:
                    print(f"INFO: {remaining_blocks} blocks for Lab + Embedded subject {subject['name']} in section {section} could not be placed and will result in free slots ('-').")

            # Process Embedded-Only Subjects (Block Size 2)
            print(f"DEBUG: Section {section} - Attempting to place Embedded-Only blocks: {[s['name'] for s in embedded_only_subjects]}")
            random.shuffle(embedded_only_subjects) # Shuffle for fairness
            for subject in embedded_only_subjects:
                block_size = 2
                blocks_needed = math.ceil(subject["credits"] / block_size)
                emb_label = subject['name'] # Label is just the subject name

                print(f"DEBUG:    Processing Embedded-Only subject: {subject['name']}, Credits: {subject['credits']}, Block Size: {block_size}, Blocks Needed: {blocks_needed}. Generated Label: {emb_label}")

                blocks_placed_count = 0
                # Attempt contiguous placement for Embedded-Only subjects
                for _ in range(blocks_needed):
                    placed = False
                    random.shuffle(list(range(self.num_days))) # Shuffle days
                    for day in range(self.num_days):
                        # Check if any lab or embedded subject is already placed on this day
                        is_lab_or_embedded_on_day = any(
                            self.timetables[section][session][day] is not None and any(
                                self.timetables[section][session][day] == s["name"] or self.timetables[section][session][day] == f"{s['name']} (LAB)"
                                for s in pure_lab_subjects + lab_embedded_subjects + embedded_only_subjects
                            ) for session in range(self.num_sessions) if session not in self.break_slots
                        )
                        if is_lab_or_embedded_on_day:
                            # print(f"DEBUG:    Skipping day {day} for {subject['name']} (Embedded-Only) due to existing lab/embedded on this day.")
                            continue # Skip this day if a lab or embedded is already placed

                        sessions_placed_today = sum(1 for session in range(self.num_sessions) if self.timetables[section][session][day] == emb_label)
                        if sessions_placed_today >= block_size:
                            continue

                        possible_starts = [session for session in range(self.num_sessions) if session not in self.break_slots]

                        # Special constraint for 1-credit embedded-only subjects: only allow placement from session 5 onwards
                        if subject["credits"] == 1:
                            possible_starts = [session for session in possible_starts if session >= 5]
                            print(f"DEBUG:    {subject['name']} (1-credit embedded-only) - Restricting possible starts to sessions {possible_starts}")

                        random.shuffle(possible_starts)

                        for start in possible_starts:
                            block_indices = list(range(start, start + block_size))
                            # Ensure indices are within bounds and not in break slots
                            if any(idx >= self.num_sessions or idx in self.break_slots for idx in block_indices):
                                continue

                            clash = False
                            for offset in range(block_size):
                                idx = start + offset
                                if self.timetables[section][idx][day] is not None:
                                    clash = True
                                    break
                                for other_section in self.sections:
                                    if subject["faculty"] in self.global_faculty_schedule[day][idx]:
                                        clash = True
                                        break
                                if clash:
                                    break

                            if not clash:
                                print(f"DEBUG:    Placing block of {emb_label} starting at session {start}, day {day}.")
                                for offset in range(block_size):
                                    idx = start + offset
                                    self.timetables[section][idx][day] = emb_label
                                    self.global_faculty_schedule[day][idx].add(subject["faculty"])
                                blocks_placed_count += 1
                                placed = True
                                break
                        if placed:
                            break

                # Remaining blocks for Embedded-Only (if any) are left as '-'
                remaining_blocks = blocks_needed - (blocks_placed_count // block_size if block_size > 0 else 0)
                if remaining_blocks > 0:
                    print(f"INFO: {remaining_blocks} blocks for Embedded-Only subject {subject['name']} in section {section} could not be placed and will result in free slots ('-').")

        # Step 2: Allocate theory subjects (strictly by credit count)
        for section in self.sections:
            subjects = self.subjects_per_section[section]
            regular_subjects = [s for s in subjects if not s["is_lab"] and not (s.get("embedded", False) and not s["is_lab"])]
            subject_periods_left = {s["name"]: s["credits"] for s in regular_subjects}

            # Separate 1-credit non-lab subjects for prioritized placement
            one_credit_non_lab_subjects = [s for s in regular_subjects if s["credits"] == 1 and not s["is_lab"]]
            other_regular_subjects = [s for s in regular_subjects if s not in one_credit_non_lab_subjects]

            # Build a list of all available slots (session, day) that are not breaks or already filled
            available_slots = [
                (session, day)
                for day in range(self.num_days)
                for session in range(self.num_sessions)
                if session not in self.break_slots and self.timetables[section][session][day] is None
            ]

            # Prioritize placing 1-credit non-lab subjects in afternoon slots (6, 7, 8)
            afternoon_slots_for_one_credit = [(s, d) for (s, d) in available_slots if s in [6, 7, 8]]
            random.shuffle(afternoon_slots_for_one_credit)

            print(f"DEBUG: Section {section} - Attempting to place 1-credit non-lab subjects: {[s['name'] for s in one_credit_non_lab_subjects]}")
            print(f"DEBUG: Available afternoon slots for 1-credit subjects: {afternoon_slots_for_one_credit}")

            for subject in one_credit_non_lab_subjects:
                count = 0
                subject_name = subject["name"]
                needed = subject["credits"]
                placed_slots = []

                print(f"DEBUG:    Processing 1-credit subject: {subject_name}, Credits needed: {needed}")

                for idx, (session, day) in enumerate(afternoon_slots_for_one_credit):
                    if count == needed:
                        print(f"DEBUG:    {subject_name} fully allocated.")
                        break

                    # No faculty clash
                    if subject["faculty"] in self.global_faculty_schedule[day][session]:
                        # print(f"DEBUG:    Skipping slot ({session}, {day}) for {subject_name} due to faculty clash.")
                        continue
                    # No repeat in a day
                    if subject_name in [self.timetables[section][s][day] for s in range(self.num_sessions)]:
                        # print(f"DEBUG:    Skipping slot ({session}, {day}) for {subject_name} due to repeat in day.")
                        continue

                    # Check if the slot is actually still available (might have been filled by a previous 1-credit subject)
                    if self.timetables[section][session][day] is not None:
                         # print(f"DEBUG:    Skipping slot ({session}, {day}) for {subject_name} as it is already filled with {self.timetables[section][session][day]}.")
                         continue

                    # Place subject
                    print(f"DEBUG:    Placing {subject_name} at session {session}, day {day}.")
                    self.timetables[section][session][day] = subject_name
                    self.global_faculty_schedule[day][session].add(subject["faculty"])
                    placed_slots.append((session, day))
                    count += 1

                if count < needed:
                    print(f"WARNING: Could not allocate all sessions for 1-credit subject {subject_name} in section {section} (allocated {count} of {needed}). Not enough afternoon slots available or constraints not met.")

                # Remove used slots from available_slots for other subjects
                available_slots = [slot for slot in available_slots if slot not in placed_slots]
                # Remove used slots from afternoon_slots_for_one_credit (for subsequent 1-credit subjects)
                afternoon_slots_for_one_credit = [slot for slot in afternoon_slots_for_one_credit if slot not in placed_slots]

                print(f"DEBUG: Section {section} - Attempting to place other regular subjects: {[s['name'] for s in other_regular_subjects]}")
                print(f"DEBUG: Available slots for other regular subjects: {available_slots}")

            # Now place other regular subjects in remaining available slots
            random.shuffle(available_slots) # Reshuffle remaining slots
            for subject in other_regular_subjects:
                count = 0
                subject_name = subject["name"]
                needed = subject["credits"]
                placed_slots = []

                for idx, (session, day) in enumerate(available_slots):
                    if count == needed:
                        break

                    # Prevent same subject in the same session index across the week (unless subjects < days)
                    if sum(1 for d in range(self.num_days) if self.timetables[section][session][d] == subject_name) > 0 and len(regular_subjects) >= self.num_days:
                        continue

                    # No faculty clash
                    if subject["faculty"] in self.global_faculty_schedule[day][session]:
                        continue
                    # No repeat in a day
                    if subject_name in [self.timetables[section][s][day] for s in range(self.num_sessions)]:
                        continue
                    # No subject in same session on consecutive days
                    if day > 0 and self.timetables[section][session][day-1] == subject_name:
                        continue

                    # Place subject
                    self.timetables[section][session][day] = subject_name
                    self.global_faculty_schedule[day][session].add(subject["faculty"])
                    placed_slots.append((session, day))
                    count += 1

                if count < needed:
                     print(f"WARNING: Could not allocate all sessions for subject {subject_name} in section {section} (allocated {count} of {needed})")

                # Remove used slots from available_slots
                available_slots = [slot for slot in available_slots if slot not in placed_slots]

            # Fallback: Force-place any remaining unallocated subject sessions into any available slot, overriding constraints
            # This fallback is now simplified as prioritized placement should handle 1-credit rules
            all_regular_subjects = one_credit_non_lab_subjects + other_regular_subjects
            print(f"DEBUG: Section {section} - Attempting to force-place any remaining sessions for all regular subjects.")
            for subject in all_regular_subjects:
                remaining = subject["credits"] - sum(
                    1 for session in range(self.num_sessions) for day in range(self.num_days)
                    if self.timetables[section][session][day] == subject["name"]
                )
                if remaining > 0:
                    print(f"DEBUG:    Subject {subject['name']} needs {remaining} more sessions to reach {subject['credits']} credits (found {subject['credits'] - remaining} placed so far).")
                    print(f"DEBUG:    Force-placing {remaining} remaining sessions for {subject['name']}.")
                    # Find any available slot (not break, not already filled)
                    force_slots = [
                        (session, day)
                        for day in range(self.num_days)
                        for session in range(self.num_sessions)
                        if session not in self.break_slots and self.timetables[section][session][day] is None
                    ]
                    # For 1-credit non-lab, only consider afternoon slots (6,7,8)
                    if subject["credits"] == 1 and not subject["is_lab"]:
                         force_slots = [(s, d) for (s, d) in force_slots if s in [6, 7, 8]]

                    for i in range(remaining):
                        if i < len(force_slots):
                            s, d = force_slots[i]
                            self.timetables[section][s][d] = subject["name"]
                            # Note: Faculty clash and other constraints are ignored in force-placement
                        else:
                            print(f"ERROR: Not enough slots to force-place all remaining sessions for subject {subject['name']} in section {section}.")

        # Step 3: Guarantee 9x5 grid for every section, no None or undefined
        for section in self.sections:
            while len(self.timetables[section]) < 9:
                self.timetables[section].append(["-"] * 5)
            for session in range(9):
                if len(self.timetables[section][session]) < 5:
                    self.timetables[section][session] += ["-"] * (5 - len(self.timetables[section][session]))
                elif len(self.timetables[section][session]) > 5:
                    self.timetables[section][session] = self.timetables[section][session][:5]
                for day in range(5):
                    if self.timetables[section][session][day] is None or self.timetables[section][session][day] == "undefined":
                        self.timetables[section][session][day] = "-"

        print('--- DEBUG: Final Timetables ---')
        for section, grid in self.timetables.items():
            print(f'Section: {section}')
            for session in range(len(grid)):
                print(f'Session {session}: {grid[session]}')

        # Synchronize free periods across all sections
        # for session in range(self.num_sessions):
        #     for day in range(self.num_days):
        #         # If any section has a free period in this slot, all should (unless it's a break or already a subject/lab)
        #         any_free = any(
        #             self.timetables[section][session][day] == '-' or not self.timetables[section][session][day]
        #             for section in self.sections
        #         )
        #         is_break = any(
        #             self.timetables[section][session][day] == 'BREAK/LUNCH'
        #             for section in self.sections
        #         )
        #         if any_free and not is_break:
        #             for section in self.sections:
        #                 # Only overwrite if not a subject/lab/break
        #                 if self.timetables[section][session][day] == '-' or not self.timetables[section][session][day]:
        #                     self.timetables[section][session][day] = '-'

        # Ensure all sections have the same number of free sessions
        # free_counts = {section: sum(
        #     1 for session in range(self.num_sessions) for day in range(self.num_days)
        #     if self.timetables[section][session][day] == '-'
        # ) for section in self.sections}
        # max_free = max(free_counts.values())
        # for section in self.sections:
        #     deficit = max_free - free_counts[section]
        #     if deficit > 0:
        #         # Find all non-break, non-filled slots
        #         available_slots = [
        #             (session, day)
        #             for session in range(self.num_sessions)
        #             for day in range(self.num_days)
        #             if self.timetables[section][session][day] not in ('BREAK/LUNCH', '-')
        #         ]
        #         # Separate morning (sessions 0,1,3) and afternoon (sessions 4,6,7,8) slots
        #         morning_sessions = [0, 1, 3, 4]  # Session I, II, III, VI (0-based)
        #         afternoon_sessions = [6, 7, 8]  # Session V, VI, VII (0-based)
        #         afternoon_slots = [(s, d) for (s, d) in available_slots if s in afternoon_sessions]
        #         morning_slots = [(s, d) for (s, d) in available_slots if s in morning_sessions]
        #         random.shuffle(afternoon_slots)
        #         random.shuffle(morning_slots)
        #         # Place free sessions in afternoon slots first
        #         placed = 0
        #         for i in range(deficit):
        #             if i < len(afternoon_slots):
        #                 s, d = afternoon_slots[i]
        #                 self.timetables[section][s][d] = '-'
        #                 placed += 1
        #         # If not enough afternoon slots, warn and fill morning slots only if necessary
        #         if placed < deficit:
        #             for i in range(deficit - placed):
        #                 if i < len(morning_slots):
        #                     s, d = morning_slots[i]
        #                     self.timetables[section][s][d] = '-'
        #                 else:
        #                     print(f"WARNING: Not enough available slots to place all free sessions in section {section} without using morning sessions.")

        # Final validation: Ensure credit==1 non-lab, non-lab+embedded subjects are only in afternoon sessions
        # Keep this validation to report if any 1-credit non-lab subject was incorrectly placed in a morning session.
        for section in self.sections:
            subjects = self.subjects_per_section[section]
            one_credit_subjects = [s["name"] for s in subjects if s["credits"] == 1 and not s["is_lab"] and not (s.get("embedded", False) and s["is_lab"])]
            for session in [0, 1, 3, 4]:  # Morning sessions (before lunch)
                for day in range(self.num_days):
                    cell = self.timetables[section][session][day]
                    if cell in one_credit_subjects:
                        print(f"ERROR: Credit==1 subject '{cell}' (not lab/lab+embedded) placed in morning session (session {session+1}, day {day+1}) in section {section}.")
        return self.timetables 