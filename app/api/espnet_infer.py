from fusion import tts

MODEL_DIR = "/home/info/espnet/egs2/vctk/tts1/exp"  # or your actual model directory


def inference_pipeline(text, lang='en', speaker=None):
    model_map = {
        "en": "espnet/kan-bayashi_ljspeech_vits",
        "es": "espnet/kan-bayashi_css10_spanish_vits",
        "fr": "espnet/kan-bayashi_css10_french_vits",
        # Add more as needed
    }

    if lang not in model_map:
        raise ValueError(f"Unsupported TTS language: {lang}")

    model_tag = model_map[lang]
    return run_tts(model_tag=model_tag, text=text, speaker=speaker)
