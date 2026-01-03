from enum import Enum
from dataclasses import dataclass
import os

class QuestionCategory(Enum):
    BASIC_UNDERSTANDING = "📘 Basic understanding questions"
    TECHNICAL_EXPLANATION = "🔍 Technical explanation"
    VULNERABILITY_ID = "⚠ Vulnerability identification"
    PREVENTION_METHODS = "🛡 Prevention methods"
    EXAMPLE_SCENARIOS = "💥 Example scenarios"
    REFERENCES = "🔗 References"
    STATISTICS = "📊 Statistics"
    PROACTIVE_SUGGESTIONS = "🧠 Proactive suggestions"

class OWASPTopic(Enum):
    BROKEN_ACCESS_CONTROL = "A01_2021_Broken_Access_Control"
    CRYPTOGRAPHIC_FAILURES = "A02_2021_Cryptographic_Failures"
    INJECTION = "A03_2021_Injection"
    INSECURE_DESIGN = "A04_2021_Insecure_Design"
    SECURITY_MISCONFIGURATION = "A05_2021_Security_Misconfiguration"
    VULNERABLE_COMPONENTS = "A06_2021_Vulnerable_Components"
    IDENTIFICATION_AUTHENTICATION_FAILURES = "A07_2021_Identification_Authentication_Failures"
    SOFTWARE_INTEGRITY_FAILURES = "A08_2021_Software_Integrity_Failures"
    SECURITY_LOGGING_MONITORING_FAILURES = "A09_2021_Security_Logging_Monitoring_Failures"
    SERVER_SIDE_REQUEST_FORGERY = "A10_2021_Server_Side_Request_ForT_Forgery"

@dataclass
class QueryContext:
    category: QuestionCategory
    requires_technical_depth: bool
    needs_examples: bool
    requires_references: bool

PROMPT_TEMPLATES_FILE_PATH = os.path.join(os.getcwd(), 'Prompt_templates', 'prompt_templates.json')