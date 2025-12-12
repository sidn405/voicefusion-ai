# fix_xtts.py
import torch.serialization
from TTS.tts.configs.xtts_config import XttsConfig

# Add safe globals for XTTS
torch.serialization.add_safe_globals([XttsConfig])

print("✅ XTTS safe globals added")