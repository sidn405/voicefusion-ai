from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from transformers import MarianMTModel, MarianTokenizer
from langdetect import detect
from functools import lru_cache

router = APIRouter()

class TranslationRequest(BaseModel):
    text: str
    source_lang: str = None  # Optional now
    target_lang: str

@lru_cache()
def load_model(src: str, tgt: str):
    model_name = f"Helsinki-NLP/opus-mt-{src}-{tgt}"
    tokenizer = MarianTokenizer.from_pretrained(model_name)
    model = MarianMTModel.from_pretrained(model_name)
    return tokenizer, model

@router.post("/translate")
def translate_text(payload: TranslationRequest):
    try:
        # ✅ Auto-detect source language if not provided
        source_lang = payload.source_lang or detect(payload.text)

        tokenizer, model = load_model(source_lang, payload.target_lang)
        tokens = tokenizer(payload.text, return_tensors="pt", padding=True)
        outputs = model.generate(**tokens)
        translated = tokenizer.decode(outputs[0], skip_special_tokens=True)

        return {
            "translated_text": translated,
            "source_lang": source_lang,
            "target_lang": payload.target_lang
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
