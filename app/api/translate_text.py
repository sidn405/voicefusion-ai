
from transformers import MarianMTModel, MarianTokenizer

model_cache = {}

def get_translator(src_lang: str, tgt_lang: str):
    key = f"{src_lang}-{tgt_lang}"
    if key not in model_cache:
        model_name = f"Helsinki-NLP/opus-mt-{src_lang}-{tgt_lang}"
        tokenizer = MarianTokenizer.from_pretrained(model_name)
        model = MarianMTModel.from_pretrained(model_name)
        model_cache[key] = (tokenizer, model)
    return model_cache[key]

def translate_text(text: str, src_lang: str = "en", tgt_lang: str = "es") -> str:
    tokenizer, model = get_translator(src_lang, tgt_lang)
    inputs = tokenizer(text, return_tensors="pt", padding=True)
    translated = model.generate(**inputs)
    return tokenizer.decode(translated[0], skip_special_tokens=True)
