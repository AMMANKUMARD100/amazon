"""
strategy_service.py — AI Strategy & Planning advisor.
Generates structured plans for:
- Exam study schedules
- Project milestone plans
- Game/competition strategies
- Idea/startup brainstorming
- Problem-solving frameworks
"""
import re
import datetime
import math
from typing import Dict, Any, List, Optional


# ─────────────────────────────────────────────────────────────────────────────
# Exam Study Plan Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_exam_strategy(subjects: List[str], days_available: int,
                            daily_hours: float = 4.0,
                            difficulty: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Generate a day-wise exam study strategy.
    
    Args:
        subjects: list of subject names
        days_available: total days until exam
        daily_hours: hours available per day for study
        difficulty: dict mapping subject → 'hard'|'medium'|'easy'
    
    Returns:
        dict with plan, summary, tips
    """
    if not subjects:
        return {"error": "Please provide at least one subject."}
    if days_available < 1:
        return {"error": "Days available must be at least 1."}

    difficulty = difficulty or {}
    # Weight subjects by difficulty
    weights = []
    for s in subjects:
        d = difficulty.get(s.lower(), "medium")
        w = 3 if d == "hard" else 2 if d == "medium" else 1
        weights.append(w)

    total_weight = sum(weights)
    total_study_hours = days_available * daily_hours

    # Allocate hours per subject
    allocations = {}
    for i, s in enumerate(subjects):
        hours = round((weights[i] / total_weight) * total_study_hours, 1)
        allocations[s] = hours

    # Build day-wise plan
    plan = []
    today = datetime.date.today()
    remaining = {s: allocations[s] for s in subjects}
    subject_idx = 0

    for day_num in range(1, days_available + 1):
        date_str = (today + datetime.timedelta(days=day_num - 1)).strftime("%Y-%m-%d")
        weekday = (today + datetime.timedelta(days=day_num - 1)).strftime("%A")

        # Last 2 days = revision
        if day_num >= days_available - 1:
            sessions = [{"subject": "All Subjects", "hours": daily_hours, "focus": "Full Revision & Mock Tests"}]
        else:
            sessions = []
            hours_left_today = daily_hours
            while hours_left_today > 0 and subject_idx < len(subjects):
                s = subjects[subject_idx % len(subjects)]
                if remaining.get(s, 0) <= 0:
                    subject_idx += 1
                    continue
                alloc = min(hours_left_today, remaining[s], 2.0)  # Max 2h per session
                d_level = difficulty.get(s.lower(), "medium")
                focus = _get_focus_tip(s, d_level)
                sessions.append({"subject": s, "hours": round(alloc, 1), "focus": focus})
                remaining[s] = round(remaining[s] - alloc, 1)
                hours_left_today -= alloc
                if remaining.get(s, 0) <= 0:
                    subject_idx += 1

        plan.append({
            "day": day_num,
            "date": date_str,
            "weekday": weekday,
            "sessions": sessions,
            "total_hours": daily_hours
        })

    # Generate summary
    summary_parts = [f"📚 {days_available}-Day Exam Study Plan for {len(subjects)} subject(s)."]
    for s, h in allocations.items():
        d = difficulty.get(s.lower(), "medium")
        summary_parts.append(f"  • {s}: {h}h total ({d} difficulty)")
    summary_parts.append(f"  • Last 2 days reserved for full revision and mock tests.")

    tips = [
        "Use the Pomodoro technique: 25 min study + 5 min break.",
        "Start with the hardest subject when your mind is freshest.",
        "Solve previous year question papers in the last 2 days.",
        "Get 7-8 hours of sleep — it consolidates memory.",
        "Use active recall (flashcards) rather than passive re-reading."
    ]

    return {
        "type": "exam_strategy",
        "subjects": subjects,
        "days": days_available,
        "daily_hours": daily_hours,
        "allocations": allocations,
        "plan": plan,
        "summary": "\n".join(summary_parts),
        "tips": tips,
        "spoken": f"I've created a {days_available}-day study plan for {', '.join(subjects)}. "
                  f"You'll study {daily_hours} hours daily. The hardest subjects get more time. "
                  f"Last 2 days are reserved for full revision."
    }


def _get_focus_tip(subject: str, difficulty: str) -> str:
    """Return a contextual study tip for a subject."""
    s = subject.lower()
    if any(k in s for k in ["math", "maths", "calculus", "algebra", "stats"]):
        return "Practice problems and formula derivations"
    if any(k in s for k in ["physics", "chem", "chemistry"]):
        return "Solve numerical problems and revise formulas"
    if any(k in s for k in ["code", "program", "cs", "computer", "data structure"]):
        return "Write code, trace through algorithms"
    if any(k in s for k in ["history", "social", "civics", "political"]):
        return "Read notes, create timelines, mind maps"
    if any(k in s for k in ["english", "literature", "language"]):
        return "Practice essays, read key texts"
    if any(k in s for k in ["bio", "biology", "anatomy"]):
        return "Draw diagrams, memorize terms"
    return "Review notes, summarize key concepts"


# ─────────────────────────────────────────────────────────────────────────────
# Project Strategy Generator
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_PHASES = {
    "app": [
        ("Planning & Requirements", 0.10, "Define features, tech stack, wireframes"),
        ("Database Design", 0.10, "Design schema, ERD, API contracts"),
        ("Backend Development", 0.30, "Build APIs, authentication, core logic"),
        ("Frontend Development", 0.25, "Build UI, connect APIs, responsiveness"),
        ("Testing & QA", 0.15, "Unit tests, integration tests, bug fixes"),
        ("Deployment & Launch", 0.10, "Deploy to cloud, set up CI/CD, go live"),
    ],
    "website": [
        ("Requirements & Design", 0.15, "Wireframes, color scheme, content plan"),
        ("Frontend Development", 0.45, "HTML/CSS/JS, responsive design"),
        ("Backend & CMS", 0.20, "Server, database, content management"),
        ("Testing", 0.10, "Cross-browser testing, mobile testing"),
        ("Launch", 0.10, "Domain, hosting, SEO basics"),
    ],
    "ml": [
        ("Problem Definition", 0.08, "Define objective, success metrics"),
        ("Data Collection", 0.15, "Gather, label, and clean dataset"),
        ("Exploratory Analysis", 0.12, "EDA, visualizations, feature understanding"),
        ("Feature Engineering", 0.15, "Transform and select features"),
        ("Model Training", 0.20, "Train, tune hyperparameters"),
        ("Evaluation", 0.15, "Accuracy, precision/recall, confusion matrix"),
        ("Deployment", 0.15, "API wrapping, monitoring"),
    ],
    "generic": [
        ("Planning", 0.15, "Define goals, timeline, resources"),
        ("Research & Design", 0.15, "Study domain, create architecture"),
        ("Development Phase 1", 0.25, "Core features implementation"),
        ("Development Phase 2", 0.20, "Secondary features, integrations"),
        ("Testing & Review", 0.15, "QA, feedback, refinements"),
        ("Launch & Handover", 0.10, "Deploy, document, present"),
    ]
}


def generate_project_strategy(project_name: str, project_type: str,
                               days_available: int,
                               team_size: int = 1,
                               goals: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Generate a project milestone plan.
    
    Args:
        project_name: Name of the project
        project_type: 'app' | 'website' | 'ml' | 'generic'
        days_available: total days for the project
        team_size: number of people
        goals: list of specific goals/features
    """
    ptype = project_type.lower()
    if "machine learning" in ptype or " ml " in f" {ptype} " or "ai" in ptype:
        phases = PROJECT_PHASES["ml"]
    elif "app" in ptype or "mobile" in ptype or "android" in ptype or "ios" in ptype:
        phases = PROJECT_PHASES["app"]
    elif "web" in ptype or "website" in ptype:
        phases = PROJECT_PHASES["website"]
    else:
        phases = PROJECT_PHASES["generic"]

    today = datetime.date.today()
    milestones = []
    current_day = 0

    for phase_name, ratio, description in phases:
        phase_days = max(1, round(days_available * ratio))
        start_date = (today + datetime.timedelta(days=current_day)).strftime("%Y-%m-%d")
        end_date = (today + datetime.timedelta(days=current_day + phase_days - 1)).strftime("%Y-%m-%d")
        milestones.append({
            "phase": phase_name,
            "start": start_date,
            "end": end_date,
            "days": phase_days,
            "description": description
        })
        current_day += phase_days

    deadline = (today + datetime.timedelta(days=days_available)).strftime("%Y-%m-%d")

    # Best practices
    best_practices = [
        "Use Git for version control — commit daily.",
        f"With {team_size} person(s), divide tasks clearly and track progress.",
        "Build a working MVP (Minimum Viable Product) first, then add features.",
        "Test each component as you build it — don't leave testing to the end.",
        "Document your API and architecture decisions as you go.",
        "Keep a daily standup: What did I do? What will I do? Any blockers?"
    ]

    spoken = (f"Here's your {days_available}-day plan for '{project_name}'. "
              f"It has {len(milestones)} phases. "
              f"Start with {milestones[0]['phase']} and aim to finish by {deadline}. "
              f"Focus on building an MVP first, then iterate.")

    return {
        "type": "project_strategy",
        "project_name": project_name,
        "project_type": project_type,
        "days": days_available,
        "team_size": team_size,
        "deadline": deadline,
        "milestones": milestones,
        "best_practices": best_practices,
        "goals": goals or [],
        "spoken": spoken
    }


# ─────────────────────────────────────────────────────────────────────────────
# Idea Advisor / Suggestion Engine
# ─────────────────────────────────────────────────────────────────────────────

IDEA_TEMPLATES = {
    "startup": [
        "Validate your idea by talking to at least 10 potential users before building.",
        "Define your target audience precisely — who exactly will pay for this?",
        "Build a landing page to test interest before writing code.",
        "Focus on solving one problem exceptionally well (avoid feature creep).",
        "Create a simple MVP within 2-4 weeks to get real user feedback.",
        "Look for a co-founder with complementary skills (tech + business).",
        "Apply to startup accelerators like Y Combinator, Techstars, or local incubators.",
        "Revenue model options: SaaS subscription, freemium, marketplace commission, one-time purchase."
    ],
    "app": [
        "Start with user stories: 'As a user, I want to... so that...'",
        "Choose your tech stack based on team expertise, not just trends.",
        "Use Figma to prototype the UI before coding.",
        "Prioritize features using the MoSCoW method (Must/Should/Could/Won't).",
        "Consider Progressive Web App (PWA) to reach both web and mobile users.",
        "Plan for scalability from day 1 — use microservices or serverless functions.",
        "Set up analytics from the start to understand user behavior.",
    ],
    "study": [
        "Use spaced repetition (Anki) to memorize facts efficiently.",
        "Teach concepts to others — the Feynman Technique is the best retention method.",
        "Group similar topics and study them together (chunking).",
        "Create mind maps to visualize relationships between concepts.",
        "Use past papers and timed mock exams to simulate real conditions.",
        "Study in 90-minute blocks (ultradian rhythm) for peak cognitive performance.",
        "Remove distractions: phone on Do Not Disturb, use Forest or Focus apps.",
    ],
    "game_strategy": [
        "Analyze your opponent's strengths and weaknesses before the game.",
        "Define your win condition clearly — what does success look like?",
        "Identify the top 3 risks and prepare counter-strategies for each.",
        "Use a SWOT analysis: Strengths, Weaknesses, Opportunities, Threats.",
        "Play to your team's strengths — build strategy around your best players.",
        "Have a contingency plan for if your primary strategy doesn't work.",
        "Stay adaptable — strategies must evolve in real-time based on how the game unfolds.",
    ],
    "general": [
        "Break the problem into smaller, solvable sub-problems.",
        "Research what others have done for similar problems — learn from existing solutions.",
        "Set clear, measurable goals with deadlines (SMART goals).",
        "Use the 80/20 rule: 20% of the effort delivers 80% of the results — find that 20%.",
        "Get feedback early and often — don't wait for perfection.",
        "Build a support network: mentors, peers, communities.",
        "Document everything so knowledge isn't lost when circumstances change.",
    ]
}


def generate_idea_suggestions(topic: str, context: str = "") -> Dict[str, Any]:
    """Generate actionable suggestions for an idea or topic."""
    combined = f"{topic} {context}".lower()

    # Detect category
    if any(k in combined for k in ["startup", "business", "company", "product", "market"]):
        category = "startup"
    elif any(k in combined for k in ["app", "website", "software", "build", "develop", "code"]):
        category = "app"
    elif any(k in combined for k in ["study", "exam", "learn", "education", "college", "school"]):
        category = "study"
    elif any(k in combined for k in ["game", "match", "cricket", "football", "tournament", "competition", "strategy"]):
        category = "game_strategy"
    else:
        category = "general"

    suggestions = IDEA_TEMPLATES[category][:6]

    return {
        "type": "idea_suggestions",
        "topic": topic,
        "category": category,
        "suggestions": suggestions,
        "spoken": f"Here are my top suggestions for '{topic}': "
                  + " ".join([f"{i+1}. {s}" for i, s in enumerate(suggestions[:3])])
    }


# ─────────────────────────────────────────────────────────────────────────────
# Problem Solver / Discussion Advisor
# ─────────────────────────────────────────────────────────────────────────────

def discuss_and_plan(query: str) -> Dict[str, Any]:
    """
    Handle open-ended discussion / problem-solving queries.
    Returns structured plan or framework.
    """
    ql = query.lower()

    # How to build / create something
    if any(k in ql for k in ["how to build", "how to create", "how to make", "how to develop", "how do i build"]):
        thing = re.sub(r"how to (build|create|make|develop|start)", "", ql).strip()
        project_type = "app" if any(k in thing for k in ["app", "website", "system"]) else "generic"
        return generate_project_strategy(thing.title(), project_type, days_available=30)

    # How to improve / get better
    if any(k in ql for k in ["how to improve", "how to get better", "how to increase", "how to boost"]):
        topic = re.sub(r"how to (improve|get better at|increase|boost)", "", ql).strip()
        return generate_idea_suggestions(topic)

    # Career / job advice
    if any(k in ql for k in ["career", "job", "internship", "placement", "resume", "interview"]):
        return {
            "type": "career_advice",
            "spoken": "For career success: build strong projects, contribute to open source, practice DSA on LeetCode, get certifications in your domain, network on LinkedIn, and prepare for system design interviews.",
            "suggestions": [
                "Build 2-3 strong portfolio projects that solve real problems.",
                "Practice Data Structures & Algorithms on LeetCode/HackerRank daily.",
                "Get certified: AWS, Google Cloud, or domain-specific certifications.",
                "Contribute to open-source projects on GitHub.",
                "Network actively on LinkedIn and attend tech meetups.",
                "Prepare for behavioral interviews using the STAR method.",
                "Apply to internships early — most open 6 months in advance.",
            ]
        }

    # Best stack / technology recommendation
    if any(k in ql for k in ["best stack", "which technology", "which framework", "what should i use", "recommend"]):
        return {
            "type": "tech_recommendation",
            "spoken": "For a full-stack web app, I recommend: React or Next.js (frontend), Node.js with Express or Python with FastAPI (backend), PostgreSQL or MongoDB (database), and deploy on AWS or Vercel.",
            "suggestions": [
                "Frontend: React.js (most popular) or Vue.js (easier to learn).",
                "Backend: Node.js + Express (JavaScript everywhere) or Python + FastAPI (fast, modern).",
                "Database: PostgreSQL (relational) or MongoDB (document-based, flexible).",
                "Mobile: React Native (cross-platform) or Flutter (beautiful UI).",
                "Cloud: AWS (industry standard), Vercel (frontend), Railway (backend).",
                "Version Control: Git + GitHub. CI/CD: GitHub Actions.",
            ]
        }

    # Default: general problem-solving framework
    return {
        "type": "problem_solving",
        "spoken": f"Let me help you think through this. First define the problem clearly, then break it into smaller parts, research existing solutions, and plan your approach step by step.",
        "framework": [
            "1. DEFINE: State the problem in one clear sentence.",
            "2. ANALYZE: What are the root causes? What constraints exist?",
            "3. RESEARCH: What solutions already exist? What can you learn from them?",
            "4. BRAINSTORM: Generate multiple possible solutions without judging.",
            "5. EVALUATE: Score solutions by feasibility, impact, and time/cost.",
            "6. PLAN: Break the chosen solution into actionable steps.",
            "7. EXECUTE & ITERATE: Start small, measure results, and improve."
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Intent Classifier for strategy queries
# ─────────────────────────────────────────────────────────────────────────────

def is_strategy_query(query: str) -> bool:
    """Return True if this is a planning/strategy/advice query."""
    ql = query.lower()
    triggers = [
        "plan", "strategy", "schedule", "how to", "how do i", "suggest",
        "advice", "recommend", "tips for", "best way", "help me",
        "what should i", "idea", "brainstorm", "discuss", "guide me",
        "roadmap", "steps to", "how can i", "career", "improve", "build"
    ]
    return any(t in ql for t in triggers)
