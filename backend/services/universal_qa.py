"""
universal_qa.py — Multi-tier universal Q&A engine.
Covers: tech, science, math, history, sports, space, biotech, coding, movies, general.
Tier 1: Local curated KB (instant, <1ms)
Tier 2: Wikipedia Wikitext infobox parser (dynamic, 200-500ms)
Tier 3: DuckDuckGo instant answers (dynamic fallback)
"""
import re
import urllib.request
import urllib.parse
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger('mcp')

# ─────────────────────────────────────────────────────────────────────────────
# Tier 1: Local curated knowledge base
# ─────────────────────────────────────────────────────────────────────────────

TECH_KB: Dict[str, str] = {
    # Programming Concepts
    "what is a rest api": "A REST API (Representational State Transfer) is a web service interface that uses HTTP methods (GET, POST, PUT, DELETE) to allow communication between client and server using stateless requests.",
    "what is recursion": "Recursion is a programming technique where a function calls itself to solve smaller sub-problems until it reaches a base case, used in algorithms like factorial, Fibonacci, and tree traversal.",
    "what is object oriented programming": "Object-Oriented Programming (OOP) is a paradigm that organizes code into objects with properties (attributes) and behaviors (methods), based on principles of Encapsulation, Inheritance, Polymorphism, and Abstraction.",
    "what is oop": "OOP (Object-Oriented Programming) organizes software into objects with data and methods, based on four pillars: Encapsulation, Inheritance, Polymorphism, and Abstraction.",
    "what is polymorphism": "Polymorphism means 'many forms' — it allows the same function or method name to behave differently based on the object or data type it operates on.",
    "what is inheritance": "Inheritance is an OOP concept where a child class acquires properties and methods from a parent class, promoting code reuse and hierarchy.",
    "what is encapsulation": "Encapsulation is bundling data (variables) and methods that operate on it within a single class, restricting direct access using access modifiers like private, protected, and public.",
    "what is abstraction": "Abstraction hides implementation details and only shows essential features to the user, achieved through abstract classes and interfaces.",
    "what is a database": "A database is an organized collection of structured data stored electronically, managed by a DBMS (Database Management System) to enable efficient data retrieval, insertion, update, and deletion.",
    "what is sql": "SQL (Structured Query Language) is a standard language for managing relational databases, used for querying, inserting, updating, and deleting data.",
    "what is nosql": "NoSQL (Not only SQL) databases store data in non-tabular formats like documents, key-value pairs, graphs, or wide-columns — examples include MongoDB, Redis, and Cassandra.",
    "what is machine learning": "Machine Learning is a subset of AI where algorithms learn patterns from data to make predictions or decisions without being explicitly programmed for each task.",
    "what is deep learning": "Deep Learning is a subset of ML that uses multi-layered neural networks (deep neural networks) to learn complex representations from large datasets, powering image recognition, NLP, and more.",
    "what is artificial intelligence": "Artificial Intelligence (AI) is the simulation of human intelligence in machines, enabling them to perform tasks like reasoning, learning, problem-solving, perception, and language understanding.",
    "what is cloud computing": "Cloud computing delivers computing services (servers, storage, databases, networking, software) over the internet on a pay-as-you-go basis, offered by providers like AWS, Azure, and Google Cloud.",
    "what is docker": "Docker is a containerization platform that packages applications and their dependencies into lightweight, portable containers that run consistently across any environment.",
    "what is kubernetes": "Kubernetes (K8s) is an open-source container orchestration system that automates deploying, scaling, and managing containerized applications.",
    "what is git": "Git is a distributed version control system that tracks code changes, enables collaboration, and manages source code history through commits, branches, and merges.",
    "what is an api": "An API (Application Programming Interface) is a set of rules and protocols that allows different software applications to communicate with each other.",
    "what is microservices": "Microservices is an architectural style that structures an application as a collection of small, independently deployable services, each responsible for a specific business function.",
    "what is devops": "DevOps is a set of practices combining software development (Dev) and IT operations (Ops) to shorten the development lifecycle and deliver high-quality software continuously.",
    "what is agile": "Agile is an iterative software development methodology that emphasizes collaboration, flexibility, and delivering working software in short cycles called sprints.",
    "what is a linked list": "A linked list is a linear data structure where elements (nodes) are connected via pointers — each node contains data and a reference to the next node.",
    "what is a binary tree": "A binary tree is a hierarchical data structure where each node has at most two children, called the left and right child.",
    "what is big o notation": "Big O Notation describes the time or space complexity of an algorithm in terms of input size, helping compare algorithm efficiency (e.g., O(n), O(log n), O(n²)).",
    "what is time complexity": "Time complexity measures how the running time of an algorithm grows as the input size increases, commonly expressed using Big O notation.",
    "what is a stack": "A stack is a linear data structure following LIFO (Last In, First Out) — elements are added and removed from the same end (top), like a pile of plates.",
    "what is a queue": "A queue is a linear data structure following FIFO (First In, First Out) — elements are added at the rear and removed from the front.",
    "what is hashing": "Hashing is converting data of any size into a fixed-size value (hash) using a hash function, used in hash tables, password storage, and data integrity checks.",
    "what is an algorithm": "An algorithm is a step-by-step procedure or set of rules for solving a specific problem or performing a computation.",
    "what is python": "Python is a high-level, interpreted, general-purpose programming language known for its simple syntax, readability, and extensive libraries — widely used in data science, web development, and AI.",
    "what is java": "Java is a high-level, object-oriented, platform-independent programming language that follows the 'Write Once, Run Anywhere' principle, widely used in enterprise and Android development.",
    "what is javascript": "JavaScript is a lightweight, interpreted scripting language primarily used for making web pages interactive — it runs in the browser and also on the server via Node.js.",
    "what is html": "HTML (HyperText Markup Language) is the standard language for creating web pages, defining the structure and content using tags like headings, paragraphs, links, and images.",
    "what is css": "CSS (Cascading Style Sheets) is a stylesheet language used to control the visual appearance of HTML elements — layout, colors, fonts, and responsiveness.",
    "what is react": "React is an open-source JavaScript library developed by Meta for building user interfaces, particularly single-page applications, using reusable UI components.",
    "what is node js": "Node.js is an open-source, cross-platform JavaScript runtime environment built on Chrome's V8 engine, enabling JavaScript to run on the server side.",
    "what is flask": "Flask is a lightweight Python web framework that provides tools for building web applications and RESTful APIs with minimal boilerplate code.",
    "what is django": "Django is a high-level Python web framework that encourages rapid development and clean, pragmatic design, with built-in features for authentication, ORM, and admin panels.",
    "what is blockchain": "Blockchain is a distributed ledger technology that records transactions in a chain of cryptographically linked blocks, making data tamper-proof and transparent without a central authority.",
    "what is cybersecurity": "Cybersecurity is the practice of protecting computer systems, networks, and data from digital attacks, unauthorized access, and damage.",
    "what is an operating system": "An operating system (OS) is system software that manages hardware resources and provides services for computer programs — examples include Windows, Linux, and macOS.",
    "what is a compiler": "A compiler is a program that translates source code written in a high-level language (like C++) into machine code (binary) that a computer can execute.",
    "what is an interpreter": "An interpreter executes source code line by line without prior compilation — Python and JavaScript use interpreters.",
    "what is virtual machine": "A virtual machine (VM) is a software emulation of a physical computer that runs an OS and applications in an isolated environment.",
}

SCIENCE_KB: Dict[str, str] = {
    # Biology & Biotech
    "what is dna": "DNA (Deoxyribonucleic Acid) is a double-helix molecule that carries the genetic instructions for the development, functioning, growth, and reproduction of all living organisms.",
    "what is rna": "RNA (Ribonucleic Acid) is a single-stranded molecule involved in protein synthesis — it carries genetic information from DNA to ribosomes where proteins are made.",
    "what is photosynthesis": "Photosynthesis is the process by which plants convert sunlight, carbon dioxide, and water into glucose and oxygen using chlorophyll, represented as: 6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂.",
    "what is respiration": "Cellular respiration is the process by which cells break down glucose using oxygen to produce ATP (energy), carbon dioxide, and water: C₆H₁₂O₆ + 6O₂ → 6CO₂ + 6H₂O + ATP.",
    "what is crispr": "CRISPR-Cas9 is a revolutionary gene-editing technology that acts as molecular scissors, allowing scientists to precisely cut, edit, or replace specific DNA sequences in any organism.",
    "what is osmosis": "Osmosis is the movement of water molecules from a region of high water potential (low solute concentration) to a region of low water potential (high solute concentration) through a semi-permeable membrane.",
    "what is mitosis": "Mitosis is cell division producing two genetically identical daughter cells — it occurs in body (somatic) cells for growth, repair, and asexual reproduction.",
    "what is meiosis": "Meiosis is cell division producing four genetically diverse haploid cells (gametes/sex cells) — it is responsible for sexual reproduction and genetic variation.",
    "what is protein": "Proteins are large biomolecules made of amino acid chains that perform virtually every function in living cells — enzymes, antibodies, structural support, and signaling.",
    "what is enzyme": "An enzyme is a biological catalyst (protein) that speeds up chemical reactions in living organisms without being consumed in the process.",
    "what is an antibiotic": "Antibiotics are drugs that kill or inhibit the growth of bacteria — they are ineffective against viral infections like the common cold or flu.",
    "what is a vaccine": "A vaccine is a biological preparation that trains the immune system to recognize and fight a specific pathogen by introducing a weakened, killed, or partial form of it.",
    "what is biotechnology": "Biotechnology is the use of living organisms, cells, or biological systems to develop products and technologies for medicine, agriculture, food production, and environmental applications.",
    "what is genetics": "Genetics is the branch of biology that studies heredity — how traits are passed from parents to offspring through genes and chromosomes.",
    # Chemistry
    "what is ph": "pH is a logarithmic scale from 0–14 measuring the acidity or alkalinity of a solution — pH below 7 is acidic, pH 7 is neutral, and pH above 7 is alkaline.",
    "what is a covalent bond": "A covalent bond is a chemical bond formed by the sharing of electron pairs between two atoms, typically between non-metal atoms.",
    "what is an ionic bond": "An ionic bond is formed when one atom transfers electrons to another, creating oppositely charged ions that attract each other — like in NaCl (table salt).",
    "what is oxidation": "Oxidation is the loss of electrons by a substance during a chemical reaction — it is always paired with reduction (the gain of electrons) in redox reactions.",
    "what is reduction": "Reduction is the gain of electrons by a substance in a chemical reaction — always paired with oxidation in redox reactions.",
    "what is acid rain": "Acid rain is precipitation with a pH below 5.6, caused by emissions of sulfur dioxide (SO₂) and nitrogen oxides (NOₓ) reacting with water in the atmosphere.",
    # Physics
    "what is newton first law": "Newton's First Law states that an object remains at rest or in uniform motion unless acted upon by an external force — also known as the Law of Inertia.",
    "what is newton second law": "Newton's Second Law states that Force = Mass × Acceleration (F = ma) — the acceleration of an object is directly proportional to the net force applied and inversely proportional to its mass.",
    "what is newton third law": "Newton's Third Law states that for every action, there is an equal and opposite reaction.",
    "what is ohms law": "Ohm's Law states that the current through a conductor is directly proportional to the voltage across it: V = IR (Voltage = Current × Resistance).",
    "what is electromagnetic induction": "Electromagnetic induction is the generation of an electric current in a conductor when it moves through a changing magnetic field, discovered by Michael Faraday.",
    "what is the doppler effect": "The Doppler Effect is the change in frequency or wavelength of a wave (sound or light) as the source and observer move relative to each other — causing the pitch change of a passing siren.",
}

MATH_KB: Dict[str, str] = {
    "what is pythagoras theorem": "The Pythagorean Theorem states that in a right-angled triangle, the square of the hypotenuse equals the sum of squares of the other two sides: a² + b² = c².",
    "what is pythagoras": "Pythagoras' Theorem: in a right-angled triangle, a² + b² = c², where c is the hypotenuse.",
    "what is factorial": "The factorial of a non-negative integer n (written n!) is the product of all positive integers up to n. Example: 5! = 5×4×3×2×1 = 120.",
    "what is fibonacci": "The Fibonacci sequence is a series where each number is the sum of the two preceding ones: 0, 1, 1, 2, 3, 5, 8, 13, 21... It appears in nature, art, and computer algorithms.",
    "what is a prime number": "A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself — examples: 2, 3, 5, 7, 11, 13.",
    "what is a quadratic equation": "A quadratic equation is of the form ax² + bx + c = 0, solved using the quadratic formula: x = (–b ± √(b²–4ac)) / 2a.",
    "what is calculus": "Calculus is the branch of mathematics studying continuous change — it has two main branches: Differential Calculus (rates of change, derivatives) and Integral Calculus (areas under curves, integrals).",
    "what is a derivative": "A derivative measures the rate of change of a function with respect to a variable — geometrically, it is the slope of the tangent line to a curve at a point.",
    "what is integration": "Integration is the reverse of differentiation — it finds the total accumulation of a quantity (area under a curve) and is a core concept in integral calculus.",
    "what is a matrix": "A matrix is a rectangular array of numbers, symbols, or expressions arranged in rows and columns — used in linear algebra, computer graphics, and machine learning.",
    "what is probability": "Probability is the measure of how likely an event is to occur, expressed as a number between 0 (impossible) and 1 (certain), calculated as P(event) = favourable outcomes / total outcomes.",
    "what is permutation": "A permutation is an arrangement of objects in a specific order. The number of permutations of n objects taken r at a time is P(n,r) = n! / (n-r)!.",
    "what is combination": "A combination is a selection of objects where order does not matter. The number of combinations of n objects taken r at a time is C(n,r) = n! / (r! × (n-r)!).",
    "what is statistics": "Statistics is the branch of mathematics dealing with data collection, analysis, interpretation, presentation, and organization to draw conclusions and make decisions.",
    "what is mean": "The mean (average) is calculated by summing all values and dividing by the count: Mean = Sum of values / Number of values.",
    "what is median": "The median is the middle value of a data set when arranged in order — if there are two middle values, the median is their average.",
    "what is mode": "The mode is the value that appears most frequently in a data set.",
}

HISTORY_KB: Dict[str, str] = {
    "when did world war 2 end": "World War II ended in Europe on May 8, 1945 (V-E Day) with Germany's surrender, and in the Pacific on September 2, 1945 (V-J Day) with Japan's formal surrender.",
    "when did world war 1 start": "World War I started on July 28, 1914, following the assassination of Archduke Franz Ferdinand of Austria-Hungary.",
    "who built the taj mahal": "The Taj Mahal was built by Mughal Emperor Shah Jahan between 1632 and 1653 as a mausoleum for his beloved wife Mumtaz Mahal, in Agra, India.",
    "who discovered america": "Christopher Columbus is credited with discovering the Americas in 1492, though Norse explorer Leif Erikson reached North America around 1000 AD.",
    "when did india get independence": "India gained independence from British rule on August 15, 1947.",
    "who was mahatma gandhi": "Mahatma Gandhi was the leader of India's non-violent independence movement against British colonial rule, known for his philosophy of Ahimsa (non-violence) and Satyagraha (truth-force).",
    "who built the great wall of china": "The Great Wall of China was built over centuries by various Chinese dynasties, primarily the Qin Dynasty (around 221 BC) and significantly expanded by the Ming Dynasty (1368–1644).",
    "what was the french revolution": "The French Revolution (1789–1799) was a period of radical political and societal change in France that overthrew the monarchy, established a republic, and led to the rise of Napoleon Bonaparte.",
    "when did the cold war end": "The Cold War ended in 1991 with the dissolution of the Soviet Union on December 25, 1991.",
    "who was nelson mandela": "Nelson Mandela was South Africa's first Black president (1994–1999), an anti-apartheid activist who spent 27 years in prison and became a global symbol of justice and reconciliation.",
    "what is the renaissance": "The Renaissance was a cultural and intellectual movement in Europe (14th–17th century) marked by a revival of art, literature, science, and learning inspired by ancient Greek and Roman culture.",
}

SPACE_KB: Dict[str, str] = {
    "which country first landed on moon": "The United States (NASA) was the first country to land humans on the Moon — Neil Armstrong and Buzz Aldrin landed on July 20, 1969 during the Apollo 11 mission.",
    "which country first landed on south pole of moon": "India was the first country to successfully land on the Moon's south pole with Chandrayaan-3's Vikram lander on August 23, 2023.",
    "what is the distance from earth to moon": "The average distance from Earth to the Moon is approximately 384,400 kilometers (238,855 miles).",
    "what is the distance from earth to sun": "The average distance from Earth to the Sun is approximately 149.6 million kilometers (93 million miles), defined as 1 Astronomical Unit (AU).",
    "what is a black hole": "A black hole is a region of spacetime with gravity so intense that nothing — not even light — can escape from it, formed when massive stars collapse at the end of their life cycle.",
    "what is the big bang": "The Big Bang theory states that the universe began approximately 13.8 billion years ago from an extremely hot, dense singularity that rapidly expanded — creating space, time, matter, and energy.",
    "what is a light year": "A light year is the distance light travels in one year through a vacuum — approximately 9.46 trillion kilometers (5.88 trillion miles).",
    "how many planets are in solar system": "There are 8 planets in our solar system: Mercury, Venus, Earth, Mars, Jupiter, Saturn, Uranus, and Neptune.",
    "what is mars": "Mars is the fourth planet from the Sun — a cold desert world with the tallest volcano (Olympus Mons) and largest canyon (Valles Marineris) in the solar system.",
    "what is the milky way": "The Milky Way is the galaxy that contains our solar system — a barred spiral galaxy approximately 100,000 light-years in diameter, containing 200–400 billion stars.",
    "what is nasa": "NASA (National Aeronautics and Space Administration) is the U.S. government agency responsible for space exploration, science, and aeronautics research.",
    "what is isro": "ISRO (Indian Space Research Organisation) is India's national space agency, known for cost-effective missions including Chandrayaan (lunar), Mangalyaan (Mars), and Gaganyaan (human spaceflight).",
    "what is the international space station": "The ISS is a habitable space station in low Earth orbit, a joint project of NASA, Roscosmos, ESA, JAXA, and CSA — continuously inhabited since November 2000.",
    "what is a satellite": "A satellite is any object that orbits a planet or star — natural satellites like the Moon, or artificial satellites launched for communication, GPS, weather, and Earth observation.",
}

GENERAL_KB: Dict[str, str] = {
    # Business & Economy
    "what is gdp": "GDP (Gross Domestic Product) is the total monetary value of all goods and services produced within a country in a specific time period — a key indicator of economic performance.",
    "what is inflation": "Inflation is the rate at which the general level of prices for goods and services rises over time, reducing the purchasing power of money.",
    "what is cryptocurrency": "Cryptocurrency is a digital or virtual currency secured by cryptography, operating on decentralized blockchain networks — Bitcoin (BTC) and Ethereum (ETH) are the most prominent examples.",
    "what is bitcoin": "Bitcoin is the first and largest decentralized digital currency, created in 2009 by the pseudonymous Satoshi Nakamoto — it operates on a peer-to-peer network without a central authority.",
    "what is a startup": "A startup is a newly established business designed to scale quickly with an innovative product or service, typically funded by venture capital, angel investors, or bootstrapping.",
    "what is stock market": "The stock market is a marketplace where shares of publicly listed companies are bought and sold, allowing companies to raise capital and investors to earn returns.",
    # Environment
    "what is climate change": "Climate change refers to long-term shifts in global temperatures and weather patterns, largely driven since the 20th century by human activities like burning fossil fuels and deforestation.",
    "what is global warming": "Global warming is the long-term rise in Earth's average temperature, primarily caused by greenhouse gas emissions (CO₂, methane) trapping heat in the atmosphere.",
    "what is renewable energy": "Renewable energy comes from naturally replenishing sources — solar, wind, hydropower, geothermal, and biomass — that do not deplete over time unlike fossil fuels.",
}

ALL_KB = {**TECH_KB, **SCIENCE_KB, **MATH_KB, **HISTORY_KB, **SPACE_KB, **GENERAL_KB}

# Normalize keys to lowercase stripped
_KB_NORMALIZED = {k.lower().strip(): v for k, v in ALL_KB.items()}


def _normalize(q: str) -> str:
    """Normalize query: lowercase, strip punctuation, collapse spaces."""
    q = q.lower().strip()
    q = re.sub(r"[?!.,;:'\"]", "", q)
    q = re.sub(r"\s+", " ", q)
    # Remove common filler words
    for filler in ["please ", "can you tell me ", "tell me ", "what exactly is ", "briefly explain ", "define "]:
        if q.startswith(filler):
            q = q[len(filler):]
    return q.strip()


def lookup_local_kb(query: str) -> Optional[str]:
    """Exact or partial KB lookup. Returns answer or None."""
    nq = _normalize(query)

    # Exact match
    if nq in _KB_NORMALIZED:
        return _KB_NORMALIZED[nq]

    # Prefix match (starts with)
    for k, v in _KB_NORMALIZED.items():
        if nq.startswith(k) or k.startswith(nq):
            if abs(len(nq) - len(k)) <= 6:
                return v

    # Keyword overlap match (≥80% keyword overlap)
    nq_words = set(nq.split())
    best_match = None
    best_score = 0.0
    for k, v in _KB_NORMALIZED.items():
        k_words = set(k.split())
        if not k_words:
            continue
        overlap = len(nq_words & k_words) / len(k_words)
        if overlap > 0.8 and overlap > best_score:
            best_score = overlap
            best_match = v
    return best_match


# ─────────────────────────────────────────────────────────────────────────────
# Tier 2: Wikipedia summary fetcher
# ─────────────────────────────────────────────────────────────────────────────

def fetch_wikipedia_summary(topic: str, sentences: int = 2) -> Optional[str]:
    """Fetch a precise summary from Wikipedia REST API."""
    try:
        clean = re.sub(r"[^a-zA-Z0-9 _]", "", topic).strip().replace(" ", "_")
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(clean)}"
        req = urllib.request.Request(url, headers={"User-Agent": "AlexaAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            extract = data.get("extract", "")
            if not extract:
                return None
            # Take first N sentences
            sent_ends = [m.end() for m in re.finditer(r"[.!?]\s", extract)]
            if sent_ends and len(sent_ends) >= sentences:
                return extract[:sent_ends[sentences - 1]].strip()
            return extract[:300].strip()
    except Exception as e:
        logger.debug(f"Wikipedia fetch failed for '{topic}': {e}")
        return None


def extract_wiki_topic(query: str) -> str:
    """Extract likely Wikipedia topic from a question."""
    nq = re.sub(r"[?!.,;:'\"]", "", query.lower()).strip()
    for prefix in [
        "what is ", "what are ", "who is ", "who was ", "who were ",
        "when did ", "when was ", "where is ", "how does ", "how do ",
        "define ", "explain ", "tell me about ", "describe "
    ]:
        if nq.startswith(prefix):
            return nq[len(prefix):].strip()
    return nq


# ─────────────────────────────────────────────────────────────────────────────
# Tier 3: DuckDuckGo Instant Answer API
# ─────────────────────────────────────────────────────────────────────────────

def fetch_duckduckgo(query: str) -> Optional[str]:
    """Fetch instant answer from DuckDuckGo API."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        req = urllib.request.Request(url, headers={"User-Agent": "AlexaAssistant/1.0"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
            answer = data.get("Answer") or data.get("AbstractText") or data.get("Definition")
            if answer and len(answer) > 10:
                return answer[:280].strip()
    except Exception as e:
        logger.debug(f"DuckDuckGo fetch failed: {e}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Main public interface
# ─────────────────────────────────────────────────────────────────────────────

def answer_question(query: str, allow_web: bool = True) -> Dict[str, Any]:
    """
    Multi-tier Q&A engine.
    Returns dict with:
      - answer: str (the precise answer)
      - source: 'local_kb' | 'wikipedia' | 'duckduckgo' | 'not_found'
      - confidence: 'high' | 'medium' | 'low'
    """
    # Tier 1: Local KB
    local = lookup_local_kb(query)
    if local:
        return {"answer": local, "source": "local_kb", "confidence": "high"}

    if not allow_web:
        return {"answer": None, "source": "not_found", "confidence": "low"}

    # Tier 2: Wikipedia
    topic = extract_wiki_topic(query)
    if len(topic) > 2:
        wiki = fetch_wikipedia_summary(topic, sentences=2)
        if wiki and len(wiki) > 30:
            return {"answer": wiki, "source": "wikipedia", "confidence": "medium"}

    # Tier 3: DuckDuckGo
    ddg = fetch_duckduckgo(query)
    if ddg:
        return {"answer": ddg, "source": "duckduckgo", "confidence": "medium"}

    return {"answer": None, "source": "not_found", "confidence": "low"}


def is_knowledge_question(query: str) -> bool:
    """Returns True if the query looks like a knowledge/factual question."""
    ql = query.lower().strip()
    knowledge_triggers = [
        "what is", "what are", "who is", "who was", "who were", "when did", "when was",
        "where is", "where was", "how does", "how do", "how many", "why is", "why does",
        "explain", "define", "what does", "tell me about", "describe", "what was",
        "which country", "which player", "which team", "which year", "what year",
        "how to", "what are the steps", "what is the formula", "formula for",
        "full form of", "abbreviation", "stands for", "meaning of"
    ]
    return any(ql.startswith(t) or t in ql for t in knowledge_triggers)
