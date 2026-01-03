from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from .chatbot_modules.chatbot import OWASPChatbot
import asyncio

router = APIRouter()

# 1. Initialize Chatbot Instance (Singleton)
# We do this globally so we don't reload models on every request
chatbot_instance = OWASPChatbot()
is_initialized = False

class ChatRequest(BaseModel):
    message: str

@router.on_event("startup")
async def startup_event():
    """Initialize chatbot components when server starts"""
    global is_initialized
    print("🤖 Initializing OWASP Chatbot components...")
    await chatbot_instance._async_init_components()
    is_initialized = True
    print("✅ Chatbot ready!")

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    API Endpoint for Next.js to call.
    Receives: { "message": "What is XSS?" }
    Returns: { "response": "...", "category": "..." }
    """
    if not is_initialized:
        raise HTTPException(status_code=503, detail="Chatbot is still initializing")

    try:
        # Generate response
        result = await chatbot_instance.process_question(request.message)
        
        # Return structured JSON
        return {
            "response": result["response"],
            "category": result.get("category", "General"),
            "context_used": result.get("context_used", False)
        }
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))