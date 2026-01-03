import time
import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from .config import CONFIG

async def get_embedding(embedding_model, text: str, embedding_cache: Dict[str, Tuple[List[float], float]]) -> Optional[List[float]]:
    """Generate embeddings with error handling, retries, and caching."""
    if not embedding_model:
        print("❌ Embedding model not available for generating embedding.")
        return None

    if text in embedding_cache:
        embedding, timestamp = embedding_cache[text]
        if time.time() - timestamp < CONFIG["EMBEDDING_CACHE_TTL_SEC"]:
            return embedding
        del embedding_cache[text]  # Clear expired entry

    for attempt in range(CONFIG["MAX_RETRIES"]):
        try:
            embedding = await asyncio.to_thread(
                embedding_model.encode,
                text,
                batch_size=CONFIG["BATCH_SIZE"],
                show_progress_bar=False,
                convert_to_numpy=True
            )
            embedding = embedding.tolist()
            embedding_cache[text] = (embedding, time.time())
            return embedding
        except Exception as e:
            print(f"Error generating embedding (attempt {attempt + 1}/{CONFIG['MAX_RETRIES']}): {e}")
            if attempt < CONFIG["MAX_RETRIES"] - 1:
                sleep_time = CONFIG["INITIAL_BACKOFF_SEC"] * (2 ** attempt)
                print(f"Retrying in {sleep_time:.1f} seconds...")
                await asyncio.sleep(sleep_time)
    return None

def calculate_keyword_overlap_score(query: str, document_text: str) -> float:
    """Calculates a score based on keyword overlap between query and document."""
    query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
    document_tokens = set(re.findall(r'\b\w+\b', document_text.lower()))

    if not query_tokens:
        return 0.0

    overlap = len(query_tokens.intersection(document_tokens))
    return overlap / len(query_tokens)

def rerank_documents(original_query: str, retrieved_documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Re-ranks retrieved documents based on keyword overlap with the original query,
    boosting documents that share more keywords.
    Assumes retrieved_documents are already dicts with 'score' and 'metadata.text'.
    """
    if not retrieved_documents:
        return []

    reranked_docs = []
    for doc in retrieved_documents:
        content = doc.get('metadata', {}).get('text', '')
        keyword_score = calculate_keyword_overlap_score(original_query, content)

        # Combine original vector score with keyword score (simple additive boost)
        doc['rerank_score'] = doc['score'] + (keyword_score * 0.1) # Small boost for keyword overlap
        reranked_docs.append(doc)

    # Sort by the new rerank_score
    reranked_docs.sort(key=lambda x: x.get('rerank_score', x['score']), reverse=True)
    return reranked_docs

def format_chat_history_for_llm(chat_history: List[Tuple[str, str]]) -> str:
    """Formats the chat history for inclusion in the LLM prompt."""
    if not chat_history:
        return ""

    formatted_history = []
    for i, (user_q, bot_r) in enumerate(chat_history):
        formatted_history.append(f"Previous Turn {i+1}:")
        formatted_history.append(f"User: {user_q}")
        formatted_history.append(f"Assistant: {bot_r}")
    return "\n".join(formatted_history) + "\n\n"

def sanitize_input(text: str) -> str:
    """
    Sanitizes user input to prevent common issues.
    - Removes excessive whitespace.
    - Strips leading/trailing spaces.
    - Basic prompt injection prevention by encoding/escaping problematic characters
      (though full prevention is complex).
    """
    # Remove null bytes
    sanitized_text = text.replace('\0', '')
    # Normalize whitespace (replace multiple spaces/tabs/newlines with a single space)
    sanitized_text = re.sub(r'\s+', ' ', sanitized_text).strip()
    # Simple encoding for characters that might interfere with prompt structure
    # (e.g., markdown backticks, instruction tags). This is a basic measure.
    sanitized_text = sanitized_text.replace('`', '\\`').replace('[INST]', '<INST>').replace('[/INST]', '</INST>')
    return sanitized_text

def format_response(response: str, category: Any) -> str: # Use Any for QuestionCategory to avoid circular import
    """Format the response based on the question category."""
    response = re.sub(r'###\s*', '', response)
    response = re.sub(r'####\s*', '', response)
    response = re.sub(r'\n{3,}', '\n\n', response)

    # Importing with full module path to avoid circular imports
    from .constants import QuestionCategory
    if category == QuestionCategory.PREVENTION_METHODS:
        response = re.sub(r'^\s*(\d+\.|-|\*)\s*', r'• ', response, flags=re.MULTILINE)
    elif category == QuestionCategory.TECHNICAL_EXPLANATION:
        response = re.sub(r'```(\w*)\n(.*?)```', r'```\1\n\2\n```', response, flags=re.DOTALL)

    return response.strip()