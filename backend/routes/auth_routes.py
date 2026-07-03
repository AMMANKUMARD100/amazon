from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from backend.auth.auth_manager import authenticate_user, load_user_by_id
from backend.database.connection import execute_query
from backend.middleware.security import rate_limit, sanitize_input
from backend.middleware.logger import log_activity, auth_logger

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
@rate_limit(limit=10, period=60)  # Rate limit login attempts
def login():
    """Authenticates the user and initiates session."""
    data = request.get_json() or {}
    username = sanitize_input(data.get("username", "")).strip()
    password = data.get("password", "")
    
    if not username or not password:
        return jsonify({"error": "ValidationFailed", "message": "Username and password are required."}), 400
        
    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "AuthenticationFailed", "message": "Invalid username or password."}), 401
        
    login_user(user, remember=True)
    
    # Log session activation
    log_activity(user.id, "LOGIN", f"User {user.username} logged in from {request.remote_addr}", request.remote_addr)
    
    return jsonify({
        "message": "Login successful.",
        "user": user.to_dict()
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """Terminates active session."""
    username = current_user.username
    user_id = current_user.id
    logout_user()
    
    log_activity(user_id, "LOGOUT", f"User {username} logged out.", request.remote_addr)
    return jsonify({"message": "Logout successful."}), 200

@auth_bp.route('/status', methods=['GET'])
def status():
    """Checks session status and returns user data."""
    if current_user.is_authenticated:
        return jsonify({
            "authenticated": True,
            "user": current_user.to_dict()
        }), 200
    return jsonify({
        "authenticated": False,
        "message": "No active session."
    }), 200

@auth_bp.route('/profile', methods=['GET', 'PUT'])
@login_required
def profile():
    """Handles fetching and updating of student profile."""
    if not current_user.is_student():
        return jsonify({"error": "Forbidden", "message": "Only students have profiles."}), 403
        
    student_id = current_user.student_id
    
    if request.method == 'GET':
        student_data = execute_query(
            "SELECT s.id, s.full_name, s.email, s.matric_number, s.current_semester, s.cgpa, u.username "
            "FROM students s JOIN users u ON s.user_id = u.id WHERE s.id = ?;",
            (student_id,),
            fetch_one=True
        )
        if not student_data:
            return jsonify({"error": "NotFound", "message": "Student profile not found."}), 404
            
        return jsonify(dict(student_data)), 200
        
    elif request.method == 'PUT':
        data = request.get_json() or {}
        email = sanitize_input(data.get("email", "")).strip()
        full_name = sanitize_input(data.get("full_name", "")).strip()
        
        if not email or not full_name:
            return jsonify({"error": "ValidationFailed", "message": "Email and Full Name are required."}), 400
            
        try:
            execute_query(
                "UPDATE students SET email = ?, full_name = ? WHERE id = ?;",
                (email, full_name, student_id),
                commit=True
            )
            log_activity(current_user.id, "UPDATE_PROFILE", f"Updated email: {email}, full_name: {full_name}", request.remote_addr)
            
            # Reload user details in session
            current_user.email = email
            current_user.full_name = full_name
            
            return jsonify({"message": "Profile updated successfully.", "email": email, "full_name": full_name}), 200
        except Exception as e:
            return jsonify({"error": "DatabaseError", "message": "Could not update profile. Email might be in use."}), 500
