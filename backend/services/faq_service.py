import json
import os
from backend.database.connection import execute_query
from backend.middleware.logger import mcp_logger

def search_faq(query_text=None):
    """Searches FAQ knowledge base using keyterms ranking."""
    query_str = (query_text or "").strip().lower()

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'database', 'faq.json')

    faqs = []
    if os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                faqs = json.load(f)
        except Exception as e:
            mcp_logger.error(f"Error reading faq.json: {e}")

    if not faqs:
        rows = execute_query("SELECT id, question, answer, category FROM faq;", fetch_all=True)
        faqs = [dict(r) for r in rows]

    if not query_str:
        return faqs

    matches = []
    words = query_str.split()
    for faq in faqs:
        question = faq.get("question", "").lower()
        answer = faq.get("answer", "").lower()
        category = faq.get("category", "").lower()

        score = 0
        for word in words:
            if word in question:
                score += 3
            if word in answer:
                score += 1
            if word in category:
                score += 2

        if score > 0:
            item = faq.copy()
            item["match_score"] = score
            matches.append(item)

    matches.sort(key=lambda x: x["match_score"], reverse=True)
    return matches
