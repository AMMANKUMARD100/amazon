import os
import sys
from flask import Flask, jsonify
from flask_cors import CORS
from flask_login import LoginManager

# Add workspace directory to path to ensure proper module resolution
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.database.connection import init_db
from backend.database.seed import seed_db
from backend.auth.auth_manager import load_user_by_id
from backend.middleware.security import add_security_headers
from backend.middleware.logger import error_logger

def create_app():
    """Application factory for CampusMate AI."""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # 1. CORS Configuration (Allow frontend on port 3000 with credentials support)
    CORS(app, resources={r"/api/*": {
        "origins": ["http://localhost:3000", "http://127.0.0.1:3000"],
        "supports_credentials": True
    }})
    
    # 2. Flask-Login Setup
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    
    @login_manager.user_loader
    def load_user(user_id):
        return load_user_by_id(user_id)
        
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({"error": "Unauthorized", "message": "Login session expired or invalid."}), 401
        
    # 3. Database Initialisation
    try:
        init_db()
        seed_db()
    except Exception as e:
        print(f"CRITICAL: Failed to initialize/seed database: {e}")
        error_logger.critical(f"Database setup failure: {e}")
        
    # 4. Blueprint Registrations
    from backend.routes.auth_routes import auth_bp
    from backend.routes.mcp_routes import mcp_bp
    from backend.routes.agent_routes import agent_bp
    from backend.routes.task_routes import tasks_bp
    from backend.routes.alexa_routes import alexa_bp
    from backend.routes.exam_routes import exam_bp
    from backend.routes.chat_routes import chat_bp
    from backend.routes.proactive_routes import proactive_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(mcp_bp, url_prefix='/api/mcp')
    app.register_blueprint(agent_bp, url_prefix='/api/agents')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks')
    app.register_blueprint(alexa_bp, url_prefix='/api/alexa')
    app.register_blueprint(exam_bp, url_prefix='/api/exams')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(proactive_bp, url_prefix='/api/proactive')

    
    # 5. Global Security Headers Middleware
    @app.after_request
    def after_request(response):
        return add_security_headers(response)
        
    # 6. Global Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({"error": "NotFound", "message": "Requested resource not found."}), 404
        
    @app.errorhandler(403)
    def forbidden_error(error):
        return jsonify({"error": "Forbidden", "message": "Access denied."}), 403
        
    @app.errorhandler(401)
    def unauthorized_error(error):
        return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
        
    @app.errorhandler(500)
    def internal_error(error):
        error_logger.error(f"500 Internal Error: {error}")
        return jsonify({"error": "InternalServerError", "message": "An unexpected error occurred on the server."}), 500
        
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Run locally offline
    app.run(host='127.0.0.1', port=port, debug=True)
