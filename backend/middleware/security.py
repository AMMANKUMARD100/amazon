import time
import re
from functools import wraps
from flask import request, jsonify, make_response, abort
from flask_login import current_user
from backend.middleware.logger import auth_logger, error_logger

# In-memory store for rate limiting (No Redis needed for offline deployment)
rate_limit_store = {}

def rate_limit(limit=60, period=60):
    """Custom rate limiting decorator using client IP. Limit is count, period is in seconds."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            now = time.time()
            
            if ip not in rate_limit_store:
                rate_limit_store[ip] = []
                
            # Filter timestamps to keep only those within current window
            rate_limit_store[ip] = [t for t in rate_limit_store[ip] if now - t < period]
            
            if len(rate_limit_store[ip]) >= limit:
                auth_logger.warning(f"Rate limit exceeded by IP: {ip} for path: {request.path}")
                return jsonify({
                    "error": "RateLimitExceeded",
                    "message": "Too many requests. Please try again later."
                }), 429
                
            rate_limit_store[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def role_required(roles):
    """Enforce authorization based on user roles (Admin/Student)."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({
                    "error": "Unauthorized",
                    "message": "Authentication required."
                }), 401
                
            if current_user.role not in roles:
                auth_logger.warning(
                    f"Unauthorized access attempt: User {current_user.username} (Role: {current_user.role}) "
                    f"attempted to access {request.path} (Required: {roles})"
                )
                return jsonify({
                    "error": "Forbidden",
                    "message": "You do not have permission to perform this action."
                }), 403
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def sanitize_input(text):
    """Simple sanitization to prevent XSS (escapes critical HTML characters)."""
    if not isinstance(text, str):
        return text
    # Escape tags
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#x27;").replace("/", "&#x2F;")
    return text

def validate_assignment_input(data):
    """Validates assignment payload inputs."""
    errors = []
    title = data.get("title", "").strip()
    due_date = data.get("due_date", "").strip()
    priority = data.get("priority", "Medium").strip()
    
    if not title:
        errors.append("Title is required.")
    elif len(title) > 100:
        errors.append("Title cannot exceed 100 characters.")
        
    if not due_date:
        errors.append("Due date is required.")
    elif not re.match(r"^\d{4}-\d{2}-\d{2}$", due_date):
        errors.append("Due date must be in YYYY-MM-DD format.")
        
    if priority not in ["High", "Medium", "Low"]:
        errors.append("Priority must be High, Medium, or Low.")
        
    return errors

def add_security_headers(response):
    """Appends defensive HTTP security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com;"
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy'] = 'no-referrer-when-downgrade'
    return response
