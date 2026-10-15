"""Proactive Alerts and Voice Agent REST API routes.

New endpoints for proactive intelligence and voice orchestration.
Does NOT modify any existing route files.
"""

from flask import Blueprint, jsonify, request

from backend.services.proactive_service import (
    check_attendance_risk,
    check_deadline_conflicts,
    generate_weekly_summary,
    get_proactive_alerts
)
from backend.agents.voice_agent import handle_voice_request

proactive_bp = Blueprint('proactive', __name__)


@proactive_bp.route('/alerts/<int:student_id>', methods=['GET'])
def api_get_alerts(student_id):
    """GET /api/proactive/alerts/<student_id> - Get all proactive alerts."""
    try:
        alerts = get_proactive_alerts(student_id)
        return jsonify({"success": True, "alerts": alerts, "count": len(alerts)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@proactive_bp.route('/alerts/<int:student_id>/attendance-risk', methods=['GET'])
def api_attendance_risk(student_id):
    """GET /api/proactive/alerts/<student_id>/attendance-risk - Attendance risk alerts."""
    try:
        risks = check_attendance_risk(student_id)
        return jsonify({"success": True, "risks": risks, "count": len(risks)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@proactive_bp.route('/alerts/<int:student_id>/deadline-conflicts', methods=['GET'])
def api_deadline_conflicts(student_id):
    """GET /api/proactive/alerts/<student_id>/deadline-conflicts - Deadline conflict alerts."""
    try:
        conflicts = check_deadline_conflicts(student_id)
        return jsonify({"success": True, "conflicts": conflicts, "count": len(conflicts)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@proactive_bp.route('/summary/<int:student_id>/weekly', methods=['GET'])
def api_weekly_summary(student_id):
    """GET /api/proactive/summary/<student_id>/weekly - Weekly performance summary."""
    try:
        summary = generate_weekly_summary(student_id)
        return jsonify({"success": True, "summary": summary}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@proactive_bp.route('/voice/<int:student_id>', methods=['POST'])
def api_voice_request(student_id):
    """POST /api/proactive/voice/<student_id> - Process voice utterance through VoiceAgent.
    
    Body: {"utterance": "plan my evening"}
    """
    try:
        data = request.get_json(silent=True) or {}
        utterance = data.get("utterance", "")
        if not utterance:
            return jsonify({"success": False, "error": "utterance is required"}), 400
        
        result = handle_voice_request(student_id, utterance)
        return jsonify({"success": True, **result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
