import os
import asyncio
import time
from typing import Dict, Tuple

import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from dotenv import load_dotenv

from .config import CONFIG

# Load environment variables
load_dotenv()

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- CRITICAL FIX: DISABLE SAFETY FILTERS ---
# This allows the model to discuss "attacks" and "vulnerabilities" without getting blocked.
safety_settings = {
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

# Use 1.5-flash for better Rate Limits
_GEMINI_MODEL = genai.GenerativeModel(
    "gemini-2.5-flash", 
    safety_settings=safety_settings
)

# Response cache
llm_response_cache: Dict[Tuple, Tuple[str, float]] = {}


class GeminiLLMAdapter:
    """
    Adapter to make Gemini behave like an OpenAI-style LLM
    """

    def create_completion(self, prompt: str, max_tokens: int, temperature: float, top_p: float, echo: bool = False):
        try:
            # --- CRITICAL FIX: INCREASED TOKENS ---
            response = _GEMINI_MODEL.generate_content(
                prompt,
                generation_config={
                    "temperature": temperature,
                    "top_p": top_p,
                    "max_output_tokens": 8192, # Force high token limit
                }
            )

            if not response:
                return None
            
            # Debugging: Check if the response was blocked
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                print(f"⚠️ BLOCKED: {response.prompt_feedback}")
                return {"choices": [{"text": "[Error: The response was blocked by safety filters. Please check llm_service.py settings.]"}]}

            # Return text if available
            if hasattr(response, 'text'):
                return {"choices": [{"text": response.text}]}
            else:
                return {"choices": [{"text": ""}]}

        except Exception as e:
            print(f"Gemini API Error: {e}")
            return None


# Instantiate adapter
llm_model = GeminiLLMAdapter()


async def generate_llm_response(
    prompt: str,
    max_tokens: int = 8192, # Default to 8192
    temperature: float = 0.7
) -> str:
    """
    Generate a response using Gemini with caching, retries, and backoff
    """

    cache_key = (prompt, max_tokens, temperature)

    # Cache hit
    if cache_key in llm_response_cache:
        response, timestamp = llm_response_cache[cache_key]
        if time.time() - timestamp < CONFIG["LLM_RESPONSE_CACHE_TTL_SEC"]:
            return response

    # Retry loop
    for attempt in range(CONFIG["MAX_RETRIES"]):
        try:
            response = await asyncio.to_thread(
                llm_model.create_completion,
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=CONFIG["TOP_P"],
                echo=False
            )

            if response and response.get("choices"):
                generated_text = response["choices"][0]["text"].strip()
                # Only cache if we got a real response
                if generated_text:
                    llm_response_cache[cache_key] = (generated_text, time.time())
                    return generated_text
            
            print(f"Attempt {attempt+1}: Empty response received.")

        except Exception as e:
            print(f"Error generating LLM response (attempt {attempt + 1}): {e}")
            if attempt < CONFIG["MAX_RETRIES"] - 1:
                await asyncio.sleep(2)

    return "I'm sorry, I couldn't generate a response. The service might be busy or the topic was flagged."