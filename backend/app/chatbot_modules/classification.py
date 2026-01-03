from .constants import QuestionCategory, OWASPTopic
class Classifier:
    def __init__(self):
        self.category_cache = {}

    async def classify_question_category(self, question: str) -> QuestionCategory:
        """Classify the question into one of the predefined categories."""
        cache_key = f"category_{question[:100]}"

        if cache_key in self.category_cache:
            return self.category_cache[cache_key]

        if not question.strip():
            return QuestionCategory.BASIC_UNDERSTANDING

        question_lower = question.lower()
        
        # Check for basic understanding questions first (what is/are, define, meaning)
        if any(phrase in question_lower for phrase in ["what is", "what are", "define ", "what does ", "meaning of"]):
            return QuestionCategory.BASIC_UNDERSTANDING
            
        # Check for example scenarios
        if any(word in question_lower for word in ["example", "case study", "real-world", "real world"]):
            return QuestionCategory.EXAMPLE_SCENARIOS
            
        # Check for prevention methods
        if any(phrase in question_lower for phrase in [
            "how to prevent", "how to fix", "how to solve", "how to mitigate",
            "best way to prevent", "best practices for preventing",
            "how can i secure", "how to secure", "how to protect"
        ]):
            return QuestionCategory.PREVENTION_METHODS
            
        # Check for vulnerability identification
        if any(phrase in question_lower for phrase in [
            "how to detect", "how to identify", "how to find", "how to scan",
            "how to test for", "how to check for", "signs of", "indicators of"
        ]):
            return QuestionCategory.VULNERABILITY_ID
            
        # Check for statistics
        if any(word in question_lower for word in ["how many", "how often", "percentage", "statistic", "statistics"]):
            return QuestionCategory.STATISTICS
            
        # Check for references
        if any(phrase in question_lower for phrase in [
            "list of", "what are the", "name some", "what tools", "which tools",
            "what resources", "where can i find", "show me"
        ]):
            return QuestionCategory.REFERENCES
            
        # Check for proactive suggestions
        if any(phrase in question_lower for phrase in [
            "suggest", "recommend", "what should i use", "what's the best way",
            "how would you improve", "how to implement"
        ]):
            return QuestionCategory.PROACTIVE_SUGGESTIONS
            
        # Check for technical explanations (more specific patterns)
        if any(phrase in question_lower for phrase in [
            "how does", "explain how", "what happens when", "what is the process",
            "what is the difference between", "vs ", "versus", "compare "
        ]):
            return QuestionCategory.TECHNICAL_EXPLANATION
            
        # Default to basic understanding if no other category matches
        return QuestionCategory.BASIC_UNDERSTANDING

    async def classify_owasp_topic(self, question: str) -> OWASPTopic:
        """Classify the question to a specific OWASP Top 10 topic."""
        question_lower = question.lower()

        topic_keywords = {
            OWASPTopic.BROKEN_ACCESS_CONTROL: ["access control", "unauthorized access", "permission"],
            OWASPTopic.CRYPTOGRAPHIC_FAILURES: ["crypto", "encryption", "hash", "ssl", "tls"],
            OWASPTopic.INJECTION: ["injection", "sql", "nosql", "command"],
            OWASPTopic.INSECURE_DESIGN: ["design", "architecture"],
            OWASPTopic.SECURITY_MISCONFIGURATION: ["misconfig", "configuration"],
            OWASPTopic.VULNERABLE_COMPONENTS: ["component", "dependency", "outdated"],
            OWASPTopic.IDENTIFICATION_AUTHENTICATION_FAILURES: ["auth", "login", "password", "jwt"],
            OWASPTopic.SOFTWARE_INTEGRITY_FAILURES: ["ci/cd", "pipeline", "supply chain"],
            OWASPTopic.SECURITY_LOGGING_MONITORING_FAILURES: ["log", "monitor", "audit"],
            OWASPTopic.SERVER_SIDE_REQUEST_FORGERY: ["ssrf", "server side request"]
        }

        for topic in OWASPTopic:
            if topic.value.lower() in question_lower:
                return topic

        for topic, keywords in topic_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                return topic

        return OWASPTopic.BROKEN_ACCESS_CONTROL # Default or 'GENERAL'