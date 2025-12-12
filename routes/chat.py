import os
import openai
from openai import OpenAI
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    instructions: str = "You are VoiceFusion AI, a helpful voice assistant."

@router.post("/debug")
async def debug_payload(raw: dict):
    logger.info("🪵 DEBUG POST BODY:", raw)
    return {"received": raw}


@router.post("/")
async def chat_with_ai(request: ChatRequest):
    try:
        message_dicts = [{"role": "system", "content": request.instructions}] + [
            {"role": m.role, "content": m.content} for m in request.messages
        ]

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=message_dicts
        )

        reply = response.choices[0].message.content
        return {"reply": reply}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

