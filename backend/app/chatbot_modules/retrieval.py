import asyncio
from typing import List, Dict, Any, Optional

from .config import CONFIG
from .prompts import TOPIC_PROMPTS
from .constants import QuestionCategory, OWASPTopic
from .utils import get_embedding, rerank_documents
from .llm_service import generate_llm_response

class RetrievalManager:
    def __init__(self, components):
        self.components = components
        self.embedding_cache = {} # Should be passed from main chatbot or managed here

    async def _rewrite_query(self, query: str) -> str:
        """Expands or rewrites the user's query using an LLM for better retrieval."""
        try:
            prompt = TOPIC_PROMPTS["query_rewriter"]["prompt"].format(query=query)
            rewritten_query = await generate_llm_response(prompt, max_tokens=100, temperature=0.3)
            if rewritten_query and len(rewritten_query) > len(query) + 10:
                print(f"Rewritten query: {rewritten_query}")
                return rewritten_query
            return query
        except Exception as e:
            print(f"Error rewriting query: {e}. Using original query.")
            return query

    async def _summarize_context(self, context_text: str, question: str) -> str:
        """Summarizes long context using an LLM."""
        if len(context_text.split()) < 200: # Only summarize if context is reasonably long
            return context_text

        print("Summarizing retrieved context...")
        try:
            prompt = TOPIC_PROMPTS["context_summarizer"]["prompt"].format(context=context_text, question=question)
            summary = await generate_llm_response(prompt, max_tokens=CONFIG["MAX_CONTEXT_TOKENS"] // 2, temperature=0.4)
            return summary
        except Exception as e:
            print(f"Error summarizing context: {e}. Using full context.")
            return context_text

    async def retrieve_relevant_context(self, original_question: str, general_category: QuestionCategory, specific_owasp_topic: OWASPTopic) -> str:
        """Retrieve context from Pinecone with enhanced features."""
        if not self.components.index:
            print("❌ Pinecone index not available for context retrieval.")
            return ""

        try:
            question_for_embedding = await self._rewrite_query(original_question)
            embedding = await get_embedding(self.components.embedding_model, question_for_embedding, self.embedding_cache)
            if not embedding:
                print("❌ Embedding generation failed. Cannot retrieve context.")
                return ""

            namespaces_to_search = [specific_owasp_topic.value] if specific_owasp_topic else self.get_relevant_namespaces(general_category)

            all_matches = []
            for namespace in namespaces_to_search:
                try:
                    results = self.components.index.query(
                        vector=embedding,
                        top_k=10,
                        include_metadata=True,
                        namespace=namespace
                    )
                    all_matches.extend(results.matches)
                except Exception as e:
                    print(f"Error querying namespace {namespace}: {e}")

            # Re-rank documents
            reranked_matches = rerank_documents(original_question, all_matches)

            context_parts = []
            for match in reranked_matches[:5]:  # Take top 5 matches
                try:
                    metadata = match.metadata or {}
                    context_parts.append(f"Source: {metadata.get('source', 'Unknown')}")
                    context_parts.append(f"Content: {metadata.get('text', '')}")
                    context_parts.append("---")
                except Exception as e:
                    print(f"Error processing match: {e}")

            full_context = "\n".join(context_parts) if context_parts else "No relevant context found."

            # Summarize context if it's too long
            if len(full_context.split()) > CONFIG["MAX_CONTEXT_TOKENS"]:
                full_context = await self._summarize_context(full_context, original_question)

            return full_context

        except Exception as e:
            print(f"❌ Critical error in context retrieval: {e}. Returning no context.")
            return ""

    def get_relevant_namespaces(self, general_category: QuestionCategory) -> List[str]:
        """Get relevant Pinecone namespaces based on general question category."""
        all_owasp_namespaces = [topic.value for topic in OWASPTopic]

        if general_category == QuestionCategory.PROACTIVE_SUGGESTIONS:
            return [
                OWASPTopic.INSECURE_DESIGN.value,
                OWASPTopic.SECURITY_MISCONFIGURATION.value,
                OWASPTopic.SOFTWARE_INTEGRITY_FAILURES.value,
                OWASPTopic.SECURITY_LOGGING_MONITORING_FAILURES.value
            ]

        return all_owasp_namespaces