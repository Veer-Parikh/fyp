import json
import os
from .constants import QuestionCategory, PROMPT_TEMPLATES_FILE_PATH

DEFAULT_TOPIC_PROMPTS = {
    "category_classifier": {
        "prompt": """Analyze the following question and determine its category.
        Categories:
        1. 📘 Basic understanding - General questions about concepts
        2. 🔍 Technical explanation - In-depth technical details
        3. ⚠ Vulnerability identification - Identifying specific vulnerabilities
        4. 🛡 Prevention methods - How to prevent security issues
        5. 💥 Example scenarios - Real-world examples or case studies
        6. 🔗 References - Requests for sources or citations
        7. 📊 Statistics - Requests for data or metrics
        8. 🧠 Proactive suggestions - Recommendations not explicitly asked for

        Return only the category number (1-8) and nothing else.

        Question: {question}"""
    },
    "owasp_topic_classifier": {
        "prompt": """Analyze the following question and determine if it is directly related to one of the OWASP Top 10 2021 categories.
        Categories (return only the specific OWASP ID, e.g., A01, A02, A03, etc.):
        A01: Broken Access Control
        A02: Cryptographic Failures
        A03: Injection
        A04: Insecure Design
        A05: Security Misconfiguration
        A06: Vulnerable and Outdated Components
        A07: Identification and Authentication Failures
        A08: Software and Data Integrity Failures
        A09: Security Logging and Monitoring Failures
        A10: Server-Side Request Forgery (SSRF)

        If the question is clearly about one of these, return ONLY its ID (e.g., A03).
        If it's a general security question not directly tied to a single OWASP Top 10 category, return 'GENERAL'.

        Question: {question}"""
    },
    "query_rewriter": {
        "prompt": """Rewrite or expand the following user query to be more comprehensive and specific for a cybersecurity knowledge retrieval system. Include relevant keywords, synonyms, and related concepts that might help in finding better information. Do NOT answer the question.

        Example:
        User Query: What is XSS?
        Rewritten Query: Explain Cross-Site Scripting (XSS) vulnerability, including its types, impact, prevention methods, and real-world examples.
        Note: Don't include this in the user prompt.

        User Query: {query}
        Rewritten Query:"""
    },
    "context_summarizer": {
        "prompt": """Summarize the following security context into a concise overview. Focus on the main points relevant to the user's question, preserving key technical details and vulnerabilities. The summary should be used to answer: "{question}"

        Context:
        {context}

        Summary:"""
    },
    **{category.name.lower(): {
        "prompt": f"You are a cybersecurity expert. {category.value}. {prompt}"
    } for category, prompt in [
        (QuestionCategory.BASIC_UNDERSTANDING,
         "Provide a clear, concise explanation suitable for beginners. Include key points and simple analogies."),
        (QuestionCategory.TECHNICAL_EXPLANATION,
         "Provide a detailed technical explanation. Include relevant protocols, standards, and technical specifications."),
        (QuestionCategory.VULNERABILITY_ID,
         "Identify and explain the vulnerability. Include CVE references if available."),
        (QuestionCategory.PREVENTION_METHODS,
         "List and explain prevention methods. Include implementation details and best practices."),
        (QuestionCategory.EXAMPLE_SCENARIOS,
         "Provide real-world examples or case studies. Include what happened and lessons learned."),
        (QuestionCategory.REFERENCES,
         "Provide authoritative references, standards, and sources. Include links if available."),
        (QuestionCategory.STATISTICS,
         "Provide relevant statistics and data. Include sources and timeframes."),
        (QuestionCategory.PROACTIVE_SUGGESTIONS,
         "Provide proactive security recommendations. Include risk assessment and implementation priority.")
    ]}
}

TOPIC_PROMPTS = DEFAULT_TOPIC_PROMPTS

try:
    with open(PROMPT_TEMPLATES_FILE_PATH, 'r', encoding='utf-8') as f:
        loaded_prompts = json.load(f)
        TOPIC_PROMPTS.update(loaded_prompts)
    print("✅ prompt_templates.json loaded successfully.")
except FileNotFoundError:
    print(f"Warning: prompt_templates.json not found at {PROMPT_TEMPLATES_FILE_PATH}. Using fallback prompts.")
except json.JSONDecodeError as e:
    print(f"Error decoding prompt_templates.json at {PROMPT_TEMPLATES_FILE_PATH}: {e}. Using fallback prompts.")