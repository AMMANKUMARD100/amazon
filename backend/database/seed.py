import os
from werkzeug.security import generate_password_hash
from backend.database.connection import get_db_connection, execute_query

def seed_db():
    """Seeds the SQLite database with mock data if not already seeded."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if users already exist
        cursor.execute("SELECT COUNT(*) FROM users;")
        if cursor.fetchone()[0] > 0:
            print("Database already contains data. Skipping seeding.")
            return
        
        print("Seeding database with mock data...")
        
        # 1. Create Users
        # Student password: password123
        # Admin password: adminpassword123
        student_pw_hash = generate_password_hash("password123")
        admin_pw_hash = generate_password_hash("adminpassword123")
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);",
            ("student", student_pw_hash, "Student")
        )
        student_user_id = cursor.lastrowid
        
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?);",
            ("admin", admin_pw_hash, "Admin")
        )
        admin_user_id = cursor.lastrowid
        
        # 2. Create Students
        cursor.execute(
            "INSERT INTO students (user_id, full_name, email, matric_number, current_semester, cgpa) VALUES (?, ?, ?, ?, ?, ?);",
            (student_user_id, "Alex Mercer", "alex.mercer@campus.edu", "CS-2026-0891", 4, 3.82)
        )
        student_id = cursor.lastrowid
        
        # 3. Create Subjects
        subjects = [
            ("CS101", "Introduction to Programming", 3, "Easy"),
            ("CS102", "Data Structures & Algorithms", 4, "Hard"),
            ("CS103", "Discrete Mathematics", 3, "Medium"),
            ("CS104", "Database Management Systems", 3, "Medium"),
            ("CS105", "Software Engineering Principles", 3, "Easy")
        ]
        
        subject_ids = {}
        for code, name, credits, difficulty in subjects:
            cursor.execute(
                "INSERT INTO subjects (student_id, code, name, credits, difficulty) VALUES (?, ?, ?, ?, ?);",
                (student_id, code, name, credits, difficulty)
            )
            subject_ids[code] = cursor.lastrowid
            
        # 4. Create Timetable
        # Days: Monday to Friday
        timetable_entries = [
            ("CS101", "Monday", "09:00", "10:30", "LH-101"),
            ("CS102", "Monday", "11:00", "12:30", "Lab-2"),
            ("CS103", "Tuesday", "09:00", "10:30", "LH-102"),
            ("CS104", "Tuesday", "14:00", "15:30", "LH-104"),
            ("CS105", "Wednesday", "10:00", "11:30", "LH-105"),
            ("CS101", "Wednesday", "13:00", "14:30", "LH-101"),
            ("CS102", "Thursday", "11:00", "12:30", "Lab-2"),
            ("CS104", "Thursday", "14:00", "15:30", "LH-104"),
            ("CS103", "Friday", "09:00", "10:30", "LH-102"),
            ("CS105", "Friday", "11:00", "12:30", "LH-105")
        ]
        for code, day, start, end, room in timetable_entries:
            cursor.execute(
                "INSERT INTO timetable (student_id, subject_id, day_of_week, start_time, end_time, room) VALUES (?, ?, ?, ?, ?, ?);",
                (student_id, subject_ids[code], day, start, end, room)
            )
            
        # 5. Create Attendance Records (Mix of Present/Absent to test threshold warning)
        # We will create about 10 attendance records per subject
        import datetime
        base_date = datetime.date(2026, 6, 1)
        
        # CS101: 9 Present, 1 Absent (90% - Good)
        # CS102: 8 Present, 2 Absent (80% - Borderline)
        # CS103: 10 Present, 0 Absent (100% - Excellent)
        # CS104: 6 Present, 4 Absent (60% - Low, needs attention)
        # CS105: 5 Present, 5 Absent (50% - Low, needs attention)
        attendance_patterns = {
            "CS101": ["Present"] * 9 + ["Absent"],
            "CS102": ["Present"] * 8 + ["Absent"] * 2,
            "CS103": ["Present"] * 10,
            "CS104": ["Present"] * 6 + ["Absent"] * 4,
            "CS105": ["Present"] * 5 + ["Absent"] * 5
        }
        
        for code, pattern in attendance_patterns.items():
            sub_id = subject_ids[code]
            for i, status in enumerate(pattern):
                date_str = (base_date + datetime.timedelta(days=i*3)).strftime("%Y-%m-%d")
                cursor.execute(
                    "INSERT INTO attendance (student_id, subject_id, date, status) VALUES (?, ?, ?, ?);",
                    (student_id, sub_id, date_str, status)
                )
                
        # 6. Create Assignments
        assignments = [
            ("CS101", "Implement Simple Calculator", "Write a basic console-based calculator program.", 2, "Completed", "Low"),
            ("CS102", "Binary Search Tree Traversal", "Implement iterative and recursive traversals on BST.", -2, "Pending", "High"), # Due soon
            ("CS102", "Graph Shortest Path Solver", "Solve Dijkstra algorithms programmatically.", 8, "Pending", "Medium"),
            ("CS103", "Logic Proofs Set 2", "Complete exercises on mathematical induction.", 4, "Pending", "High"),
            ("CS104", "SQL Query Homework", "Write complex queries using Joins and Group By.", 12, "Pending", "Low"),
            ("CS105", "Requirement Specification Doc", "Draft complete Software Requirement Specification document.", -5, "Completed", "Medium")
        ]
        
        for code, title, description, days_delta, status, priority in assignments:
            sub_id = subject_ids[code]
            due_date = (datetime.date.today() + datetime.timedelta(days=days_delta)).strftime("%Y-%m-%d")
            cursor.execute(
                "INSERT INTO assignments (student_id, subject_id, title, description, due_date, status, priority) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (student_id, sub_id, title, description, due_date, status, priority)
            )
            
        # 7. Create Study Plans
        study_plans = [
            ("CS102", (datetime.date.today() + datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "16:00", "18:00", "Review Red-Black Trees", "Scheduled"),
            ("CS103", (datetime.date.today() + datetime.timedelta(days=2)).strftime("%Y-%m-%d"), "10:00", "12:00", "Induction Practice", "Scheduled"),
            ("CS104", (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d"), "15:00", "17:00", "Index Optimization", "Completed")
        ]
        for code, date_str, start, end, topic, status in study_plans:
            cursor.execute(
                "INSERT INTO study_plans (student_id, subject_id, date, start_time, end_time, topic, status) VALUES (?, ?, ?, ?, ?, ?, ?);",
                (student_id, subject_ids[code], date_str, start, end, topic, status)
            )
            
        # 8. Seed Campus FAQs
        faqs = [
            ("How do I contact the Academic Advisor?", "You can email advising@campus.edu or visit Room 302 in the Administration Block during walk-in hours (Mon-Wed 2-4 PM).", "Advising"),
            ("Where is the Central Library located?", "The Central Library is located in Block C, opposite the Student Union Building. It is open 24/7 during exam weeks.", "Facilities"),
            ("What is the attendance policy?", "Students must maintain at least 75% attendance in each subject to be eligible to sit for the final semester examinations.", "Policy"),
            ("How can I request an official transcript?", "Official transcript requests can be submitted online via the Student Portal under academic records. Standard processing takes 3-5 business days.", "Records"),
            ("What should I do if I miss an exam due to illness?", "You must submit a valid Medical Certificate (MC) to the Faculty Office within 48 hours of the missed exam. An make-up exam or waiver may be approved.", "Policy"),
            ("Where can I find the IT Helpdesk?", "The IT Helpdesk is located on the Ground Floor of Block D, inside the Main Computer Lab. You can also log support tickets at support.campus.edu.", "IT Support"),
            ("What are the semester credit limits?", "The standard load is 15-18 credits per semester. Overloads up to 21 credits require a CGPA of 3.5 or above and Advisor approval.", "Policy")
        ]
        for q, a, cat in faqs:
            cursor.execute(
                "INSERT INTO faq (question, answer, category) VALUES (?, ?, ?);",
                (q, a, cat)
            )
            
        # 9. Initial Notifications
        cursor.execute(
            "INSERT INTO notifications (student_id, title, message, type, is_read) VALUES (?, ?, ?, ?, ?);",
            (student_id, "Welcome to CampusMate AI!", "Your intelligent academic concierge is active. Check your dashboard for insights.", "Info", 0)
        )
        
        conn.commit()
        print("Database seeded successfully.")
    except Exception as e:
        conn.rollback()
        print(f"Error seeding database: {e}")
        raise e
    finally:
        conn.close()

if __name__ == "__main__":
    seed_db()
