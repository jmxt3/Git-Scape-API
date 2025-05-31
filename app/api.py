"""
FastAPI application creation and configuration.

Author: João Machete
"""
import os
import time
import logging
import uvicorn

from fastapi import FastAPI, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
import requests

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application
    """
    app = FastAPI(
        title=str(settings.APP_NAME),
        description=str(settings.APP_DESCRIPTION),
        version=str(settings.APP_VERSION),
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    return app

router = APIRouter()

@router.post("/chat/gemini")
def chat_with_gemini(
    api_key: str = Body(..., embed=True, description="Gemini API Key (user provided)"),
    system_instruction: str = Body(..., embed=True, description="System instruction for Gemini chat context"),
    history: list = Body(default_factory=list, embed=True, description="Chat history as a list of messages (optional)"),
    user_message: str = Body(..., embed=True, description="User's message to send to Gemini")
):
    """
    Proxy endpoint to chat with Gemini API. Accepts API key, system instruction, chat history, and user message.
    Returns Gemini's response.
    """
    # Gemini API endpoint and payload structure
    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=" + api_key
    headers = {"Content-Type": "application/json"}
    # Compose the contents for Gemini API
    contents = []
    if system_instruction:
        contents.append({"role": "user", "parts": [{"text": system_instruction}]})
    if history:
        for msg in history:
            contents.append({"role": msg.get("sender", "user"), "parts": [{"text": msg.get("text", "")}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})
    payload = {"contents": contents}
    try:
        response = requests.post(GEMINI_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        # Extract the main text response
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return {"text": text, "raw": data}
    except requests.RequestException as e:
        detail = None
        if hasattr(e, 'response') and e.response is not None:
            try:
                detail = e.response.text
            except Exception:
                detail = str(e.response)
        return {"error": str(e), "detail": detail}
