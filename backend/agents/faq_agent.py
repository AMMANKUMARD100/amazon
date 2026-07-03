from backend.agents.base_agent import BaseAgent

class FAQAgent(BaseAgent):
    """FAQAgent: Queries offline knowledge files or tables using keyterms to resolve student questions."""
    
    def run(self, query):
        """Searches FAQ database for matching records. Returns structured JSON."""
        query_str = query.strip()
        if not query_str:
            return {
                "answer": "Please ask a question, and I will search the campus directory.",
                "matches": []
            }
            
        results = self.call_mcp_tool("searchFAQ", method="POST", payload={"query": query_str})
        
        if not results:
            return {
                "answer": (
                    "I couldn't find a direct match for your question in our local database. "
                    "Please try using other keywords (e.g. 'library', 'advisor', 'attendance', 'MC') or consult the Faculty Office."
                ),
                "matches": []
            }
            
        # Top match
        top_match = results[0]
        score = top_match.get("match_score", 0)
        
        # If score is low, warn the user
        if score < 2:
            return {
                "answer": (
                    f"I found a possible reference relating to: \"{top_match['question']}\"\n\n"
                    f"Answer: {top_match['answer']}\n\n"
                    "If this is not what you were looking for, please refine your search terms."
                ),
                "matches": results
            }
            
        return {
            "answer": top_match["answer"],
            "matched_question": top_match["question"],
            "category": top_match["category"],
            "matches": results
        }
