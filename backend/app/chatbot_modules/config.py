import os
import torch
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG = {
    "PINECONE_API_KEY": os.getenv("PINECONE_API_KEY"),
    "USE_PINECONE": True,
    "USE_LOCAL_LLM": False,
    "PINECONE_ENVIRONMENT": os.getenv("PINECONE_ENVIRONMENT"),
    "PINECONE_INDEX_NAME": "owasp-qa",
    "VECTOR_DIMENSION": 768,
    "EMBEDDING_MODEL_PATH": 'all-MiniLM-L6-v2', ## './fine_tuned_owasp_model_advanced',
    "LOCAL_MODEL_DIR": "./pretrained_language_model",
    "LLM_FILENAME": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
    # "KNOWLEDGE_GRAPH_PATH": "./security_knowledge_graph.gml",
    "KNOWLEDGE_GRAPH_PATH": os.path.join(BASE_DIR, "security_knowledge_graph.gml"),
    "DEVICE": 'cuda' if torch.cuda.is_available() else 'cpu',
    "BATCH_SIZE": 8,
    "MAX_RETRIES": 3,
    "INITIAL_BACKOFF_SEC": 5,
    "TEMPERATURE": 0.8,
    "TOP_P": 0.95,
    "TOP_K": 50,
    "MAX_CHAT_HISTORY_TURNS": 5,
    "MAX_CONTEXT_TOKENS": 2500,
    "EMBEDDING_CACHE_TTL_SEC": 3600,
    "PINECONE_CACHE_TTL_SEC": 300,
    "LLM_RESPONSE_CACHE_TTL_SEC": 600,
    "LLM_GPU_LAYERS": 32 if torch.cuda.is_available() else 0, # Assuming 32 layers for GPU
    "LLM_CTX_SIZE": 2048 # Context window size for LLM
}

os.makedirs(CONFIG["LOCAL_MODEL_DIR"], exist_ok=True)