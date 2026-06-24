# config.py - Application Configuration
# ====================================================================

import os

# ============================================
# USER CONFIGURATION
# ============================================
CURRENT_USER_ID = 1

# ============================================
# AI MODEL CONFIGURATION
# ============================================
DOCTOR_MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"
STT_MODEL = "whisper-large-v3"

# ============================================
# VOICE CONFIGURATION
# ============================================
AUDIO_CACHE_DIR = "audio_cache"
MAX_AUDIO_FILES = 20
VOICE_SPEED_SLOW = True
VOICE_LANGUAGE = "en"

# ============================================
# SYSTEM PROMPT FOR AI DOCTOR
# ============================================
SYSTEM_PROMPT = """You have to act as a professional doctor, i know you are not but this is for learning purpose. 
            What's in this image?. Do you find anything wrong with it medically? 
            If you make a differential, suggest some remedies for them. Donot add any numbers or special characters in 
            your response. Your response should be in one long paragraph. Also always answer as if you are answering to a real person.
            Donot say 'In the image I see' but say 'With what I see, I think you have ....'
            Dont respond as an AI model in markdown, your answer should mimic that of an actual doctor not an AI bot, 
            Keep your answer concise (max 2 sentences). No preamble, start your answer right away please"""

# ============================================
# DATABASE CONFIGURATION
# ============================================
DB_DIR = "database"
DB_NAME = "elderly_care.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)