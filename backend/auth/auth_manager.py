from flask_login import UserMixin
from backend.database.connection import execute_query

class User(UserMixin):
    """User class matching SQLite user record for Flask-Login integration."""
    def __init__(self, user_id, username, role, student_id=None, email=None, full_name=None):
        self.id = str(user_id)
        self.username = username
        self.role = role
        self.student_id = student_id
        self.email = email
        self.full_name = full_name

    def is_admin(self):
        return self.role == 'Admin'

    def is_student(self):
        return self.role == 'Student'

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role,
            "student_id": self.student_id,
            "email": self.email,
            "full_name": self.full_name
        }

def load_user_by_id(user_id):
    """Loads a user by their user ID from SQLite, matching student details if role is Student."""
    user_row = execute_query(
        "SELECT id, username, role FROM users WHERE id = ?;",
        (user_id,),
        fetch_one=True
    )
    if not user_row:
        return None
    
    # If the user is a student, fetch their student profile info
    if user_row['role'] == 'Student':
        student_row = execute_query(
            "SELECT id, email, full_name FROM students WHERE user_id = ?;",
            (user_row['id'],),
            fetch_one=True
        )
        if student_row:
            return User(
                user_row['id'],
                user_row['username'],
                user_row['role'],
                student_id=student_row['id'],
                email=student_row['email'],
                full_name=student_row['full_name']
            )
            
    return User(user_row['id'], user_row['username'], user_row['role'])

def authenticate_user(username, password):
    """Checks credentials and returns User object if successful, else None."""
    from werkzeug.security import check_password_hash
    from backend.middleware.logger import auth_logger
    
    user_row = execute_query(
        "SELECT id, username, password_hash, role FROM users WHERE username = ?;",
        (username,),
        fetch_one=True
    )
    if not user_row:
        auth_logger.warning(f"Failed login attempt for non-existent username: {username}")
        return None
        
    if check_password_hash(user_row['password_hash'], password):
        user = load_user_by_id(user_row['id'])
        auth_logger.info(f"User logged in successfully: {username} (Role: {user.role})")
        return user
        
    auth_logger.warning(f"Incorrect password attempt for user: {username}")
    return None
