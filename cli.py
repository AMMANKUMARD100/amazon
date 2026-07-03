import sys
import os
import requests
import getpass
import datetime

# Base API url
PORT = os.environ.get('PORT', '5000')
BASE_URL = f"http://127.0.0.1:{PORT}/api"

class CampusMateCLI:
    def __init__(self):
        self.session = requests.Session()
        self.user = None
        self.is_logged_in = False
        
    def check_connection(self):
        """Verifies if Flask server is running before displaying menu."""
        try:
            # Short timeout to fail fast
            self.session.get(f"{BASE_URL}/auth/status", timeout=2)
            return True
        except requests.exceptions.RequestException:
            return False

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self, title):
        print("=" * 60)
        print(f" {title.upper()} ".center(60, "="))
        print("=" * 60)

    def print_menu(self, options):
        for idx, opt in enumerate(options, 1):
            print(f" [{idx}] {opt}")
        print("=" * 60)

    def run(self):
        if not self.check_connection():
            self.clear_screen()
            print("!" * 60)
            print(" ERROR: BACKEND SERVICES OFFLINE ".center(60, "!"))
            print("!" * 60)
            print(f"Could not connect to backend server at: {BASE_URL}")
            print("Please ensure the Flask backend app is running:")
            print("  $ python backend/app.py")
            print("!" * 60)
            input("\nPress Enter to exit...")
            return

        while True:
            self.clear_screen()
            if not self.is_logged_in:
                self.print_header("CampusMate AI Login")
                print("Welcome! Please log in to access your student concierge.")
                print("Default Mock Credentials:")
                print("  Student Username: student   | Password: password123")
                print("  Admin Username:   admin     | Password: adminpassword123")
                print("-" * 60)
                
                username = input("Username: ").strip()
                if not username:
                    continue
                password = getpass.getpass("Password: ")
                
                self.login(username, password)
            else:
                self.print_header(f"CampusMate AI - Welcome, {self.user.get('username')}")
                options = [
                    "Study Planner",
                    "Assignments",
                    "Attendance",
                    "Timetable",
                    "Reminder Dashboard",
                    "Campus FAQ Chat",
                    "Dashboard Analytics",
                    "Profile & CGPA Calculator",
                    "Logout",
                    "Exit"
                ]
                self.print_menu(options)
                choice = input("Enter choice (1-10): ").strip()
                
                if choice == "1":
                    self.show_study_planner()
                elif choice == "2":
                    self.show_assignments()
                elif choice == "3":
                    self.show_attendance()
                elif choice == "4":
                    self.show_timetable()
                elif choice == "5":
                    self.show_reminders()
                elif choice == "6":
                    self.show_faq()
                elif choice == "7":
                    self.show_dashboard_analytics()
                elif choice == "8":
                    self.show_profile()
                elif choice == "9":
                    self.logout()
                elif choice == "10":
                    print("\nThank you for using CampusMate AI. Goodbye!")
                    break
                else:
                    input("\nInvalid option. Press Enter to retry...")

    def login(self, username, password):
        try:
            res = self.session.post(f"{BASE_URL}/auth/login", json={
                "username": username,
                "password": password
            })
            if res.status_code == 200:
                data = res.json()
                self.user = data.get("user", {})
                self.is_logged_in = True
                input("\nLogin successful! Press Enter to open main menu...")
            else:
                err = res.json()
                input(f"\nLogin failed: {err.get('message', 'Invalid credentials')}. Press Enter...")
        except Exception as e:
            input(f"\nConnection error: {e}. Press Enter...")

    def logout(self):
        try:
            self.session.post(f"{BASE_URL}/auth/logout")
        except Exception:
            pass
        self.user = None
        self.is_logged_in = False
        input("\nLogged out successfully. Press Enter...")

    def show_study_planner(self):
        self.clear_screen()
        self.print_header("Study Planner Agent")
        print("Invoking PlannerAgent to structure your weekly sessions...")
        
        try:
            res = self.session.get(f"{BASE_URL}/agents/planner")
            if res.status_code == 200:
                data = res.json()
                plan = data.get("study_plan", [])
                
                if not plan:
                    print("\nNo study sessions generated. Check if you have subjects registered.")
                else:
                    print(f"\nGenerated Study Plan ({len(plan)} slots):")
                    print("-" * 65)
                    print(f"{'Date':<12} | {'Time':<15} | {'Course':<8} | {'Topic'}")
                    print("-" * 65)
                    for slot in plan:
                        print(f"{slot['date']:<12} | {slot['start_time']}-{slot['end_time']:<15} | {slot['code']:<8} | {slot['topic']}")
                    print("-" * 65)
                    
                    save_choice = input("\nWould you like to schedule/save these sessions in your calendar? (y/n): ").strip().lower()
                    if save_choice == 'y':
                        save_res = self.session.post(f"{BASE_URL}/agents/planner/save", json={"slots": plan})
                        if save_res.status_code == 201:
                            print("\nSessions saved successfully!")
                        else:
                            print("\nFailed to save sessions.")
            else:
                print(f"Error invoking PlannerAgent: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to return to menu...")

    def show_assignments(self):
        while True:
            self.clear_screen()
            self.print_header("Assignment Manager")
            
            try:
                # Let's call the Assignment Agent to fetch and group them
                res = self.session.get(f"{BASE_URL}/agents/assignments")
                if res.status_code != 200:
                    print(f"Error fetching assignments: {res.text}")
                    break
                    
                data = res.json()
                overdue = data.get("overdue", [])
                urgent = data.get("urgent", [])
                pending = data.get("pending", [])
                completed = data.get("completed", [])
                
                print("Active Assignments list:")
                print("-" * 65)
                
                if not overdue and not urgent and not pending and not completed:
                    print("  No assignments found.")
                
                if overdue:
                    print("  OVERDUE TASKS:")
                    for a in overdue:
                        print(f"    [!] ID: {a['id']:<2} | {a['code']}: {a['title']:<25} | Due: {a['due_date']} (DAYS: {a.get('days_left')})")
                if urgent:
                    print("  URGENT (DUE SOON):")
                    for a in urgent:
                        print(f"    [*] ID: {a['id']:<2} | {a['code']}: {a['title']:<25} | Due: {a['due_date']} (DAYS: {a.get('days_left')})")
                if pending:
                    print("  PENDING:")
                    for a in pending:
                        print(f"        ID: {a['id']:<2} | {a['code']}: {a['title']:<25} | Due: {a['due_date']} | Priority: {a['priority']}")
                if completed:
                    print("  COMPLETED:")
                    for a in completed:
                        print(f"        ID: {a['id']:<2} | {a['code']}: {a['title']:<25} | Status: Completed")
                        
                print("-" * 65)
                print("\nOptions: [1] Add Assignment  [2] Complete Assignment  [3] Delete  [4] Back")
                opt = input("Choice: ").strip()
                
                if opt == "1":
                    self.add_assignment_flow()
                elif opt == "2":
                    a_id = input("Enter Assignment ID to mark completed: ").strip()
                    if a_id:
                        self.session.post(f"{BASE_URL}/mcp/updateAssignment", json={"assignment_id": int(a_id), "status": "Completed"})
                elif opt == "3":
                    a_id = input("Enter Assignment ID to delete: ").strip()
                    if a_id:
                        self.session.delete(f"{BASE_URL}/mcp/deleteAssignment", json={"assignment_id": int(a_id)})
                elif opt == "4":
                    break
            except Exception as e:
                print(f"Error: {e}")
                input("\nPress Enter to return...")
                break

    def add_assignment_flow(self):
        try:
            # Let's get subjects first to allow user to pick subject_id
            sub_res = self.session.get(f"{BASE_URL}/mcp/getAttendance")
            if sub_res.status_code != 200:
                print("Could not retrieve subject lists.")
                return
            subjects = sub_res.json()
            
            # De-duplicate subjects by ID
            unique_subs = {}
            for item in subjects:
                unique_subs[item['subject_id']] = f"{item['code']} - {item['name']}"
                
            print("\nAvailable subjects:")
            for sub_id, name in unique_subs.items():
                print(f"  ID: {sub_id} | {name}")
                
            sub_id = input("\nEnter Subject ID: ").strip()
            if not sub_id:
                return
            title = input("Assignment Title: ").strip()
            due_date = input("Due Date (YYYY-MM-DD): ").strip()
            priority = input("Priority (High/Medium/Low, default Medium): ").strip() or "Medium"
            
            res = self.session.post(f"{BASE_URL}/mcp/addAssignment", json={
                "subject_id": int(sub_id),
                "title": title,
                "due_date": due_date,
                "priority": priority
            })
            if res.status_code == 201:
                print("\nAssignment added successfully.")
                input("\nPress Enter...")
            else:
                print(f"\nFailed to add assignment: {res.text}")
                input("\nPress Enter...")
        except Exception as e:
            print(f"Error adding assignment: {e}")
            input("\nPress Enter...")

    def show_attendance(self):
        self.clear_screen()
        self.print_header("Attendance Analysis Agent")
        
        try:
            res = self.session.get(f"{BASE_URL}/agents/attendance")
            if res.status_code == 200:
                data = res.json()
                print(f"\nOverall Attendance: {data['overall_percentage']}% | Status: {data['status']}")
                print("-" * 65)
                print(f"{'Course':<8} | {'Present/Total':<15} | {'Percentage':<12} | {'Action Advisory'}")
                print("-" * 65)
                for detail in data.get("details", []):
                    print(f"{detail['code']:<8} | {detail['present']}/{detail['total_classes']:<15} | {detail['percentage']:<5} | {detail['advice']}")
                print("-" * 65)
            else:
                print(f"Error fetching attendance analysis: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to return to menu...")

    def show_timetable(self):
        self.clear_screen()
        self.print_header("Weekly Timetable Viewer")
        
        try:
            res = self.session.post(f"{BASE_URL}/mcp/getTimetable")
            if res.status_code == 200:
                slots = res.json()
                if not slots:
                    print("\nNo timetable entries found.")
                else:
                    current_day = ""
                    for slot in slots:
                        if slot['day_of_week'] != current_day:
                            current_day = slot['day_of_week']
                            print(f"\n=== {current_day.upper()} ===")
                        print(f"  {slot['start_time']} - {slot['end_time']} | {slot['code']}: {slot['name']} (Room: {slot['room']})")
            else:
                print(f"Error loading timetable: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to return to menu...")

    def show_reminders(self):
        self.clear_screen()
        self.print_header("Reminder Dashboard Agent")
        
        try:
            res = self.session.get(f"{BASE_URL}/agents/reminders")
            if res.status_code == 200:
                data = res.json()
                print(f"Date: {data.get('date')} ({data.get('day')})")
                print("=" * 60)
                
                reminders = data.get("reminders", [])
                if not reminders:
                    print("\nNo classes or scheduled study items for today. Take some rest!")
                else:
                    for r in reminders:
                        print(f" [{r['type'].upper()}] - {r['time']}")
                        print(f"   Task:   {r['title']}")
                        print(f"   Detail: {r['detail']}")
                        print("-" * 60)
            else:
                print(f"Error loading reminders: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to return to menu...")

    def show_faq(self):
        self.clear_screen()
        self.print_header("Campus FAQ Chat Agent")
        print("Type your questions below regarding campus, policies, advisory or IT.")
        print("(Press Enter blank to return to menu)\n")
        
        while True:
            query = input("Student Query: ").strip()
            if not query:
                break
                
            try:
                res = self.session.post(f"{BASE_URL}/agents/faq", json={"query": query})
                if res.status_code == 200:
                    data = res.json()
                    print(f"\nAgent Answer:\n{data.get('answer')}")
                    print("-" * 60)
                else:
                    print(f"Error querying FAQ agent: {res.text}")
            except Exception as e:
                print(f"Error connecting: {e}")

    def show_dashboard_analytics(self):
        self.clear_screen()
        self.print_header("Dashboard Analytics Agent")
        
        try:
            res = self.session.get(f"{BASE_URL}/agents/dashboard")
            study_res = self.session.get(f"{BASE_URL}/agents/study")
            
            if res.status_code == 200:
                data = res.json()
                metrics = data.get("metrics", {})
                charts = data.get("charts", {})
                
                print(f"\nStudent Profile: {data.get('student_name')} | CGPA: {data.get('cgpa')}")
                print("-" * 60)
                print(f"  Overall Attendance:      {metrics.get('overall_attendance')}%")
                print(f"  Pending Assignments:     {metrics.get('pending_assignments')}")
                print(f"  Completed Assignments:   {metrics.get('completed_assignments')}")
                print(f"  Weekly Study Hours:      {metrics.get('scheduled_study_hours')} hours")
                print("-" * 60)
                
                # ASCII Attendance display
                print("\nAttendance visualizer:")
                att = charts.get("attendance", {})
                for lbl, val in zip(att.get("labels", []), att.get("data", [])):
                    bar = "#" * int(val / 5)
                    print(f"  {lbl:<6} [{bar:<20}] {val}%")
                print("-" * 60)
                
                # Active advice recommendations from StudyAgent
                if study_res.status_code == 200:
                    study_data = study_res.json()
                    recs = study_data.get("recommendations", [])
                    print("\nStudy Concierge Advisory:")
                    for rec in recs:
                        print(f"  [{rec['priority']}] - {rec['category']}:")
                        print(f"    {rec['message']}")
            else:
                print("Error loading dashboard metrics.")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to return to menu...")

    def show_profile(self):
        self.clear_screen()
        self.print_header("Profile & CGPA Calculator")
        
        try:
            res = self.session.get(f"{BASE_URL}/auth/profile")
            if res.status_code == 200:
                profile = res.json()
                print(f"\nFull Name:       {profile['full_name']}")
                print(f"Email Address:   {profile['email']}")
                print(f"Matric Number:   {profile['matric_number']}")
                print(f"Active Semester: {profile['current_semester']}")
                print(f"Cumulative CGPA: {profile['cgpa']}")
                print("=" * 60)
                
                calc_choice = input("\nWould you like to project this semester's CGPA? (y/n): ").strip().lower()
                if calc_choice == 'y':
                    self.run_cgpa_projection(profile['cgpa'])
            else:
                print(f"Error: {res.text}")
        except Exception as e:
            print(f"Error: {e}")
            
        input("\nPress Enter to return to menu...")

    def run_cgpa_projection(self, current_cgpa):
        print("\nEnter grades projected for this semester's courses:")
        print("Grades: A (4.0), B (3.0), C (2.0), D (1.0), F (0.0)")
        
        # Let's get registered courses
        try:
            sub_res = self.session.get(f"{BASE_URL}/mcp/getAttendance")
            if sub_res.status_code != 200:
                print("Could not retrieve registered courses.")
                return
            subjects = sub_res.json()
            unique_subs = {}
            for item in subjects:
                unique_subs[item['code']] = item['name']
                
            grades_payload = []
            for code, name in unique_subs.items():
                grade = input(f"  Grade for {code} ({name}): ").strip().upper()
                if grade not in ["A", "B", "C", "D", "F"]:
                    grade = "A"  # Default
                grades_payload.append({"code": code, "grade": grade})
                
            res = self.session.post(f"{BASE_URL}/mcp/calculateCGPA", json={"grades": grades_payload})
            if res.status_code == 200:
                data = res.json()
                print("-" * 60)
                print(f"Current Cumulative CGPA:   {data['current_cgpa']}")
                print(f"Projected Semester GPA:    {data['semester_gpa']}")
                print(f"New Projected CGPA:        {data['projected_cgpa']}")
                print("-" * 60)
            else:
                print("Failed to calculate CGPA projection.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    cli = CampusMateCLI()
    cli.run()
