# voice_assistant.py - Text to Speech using gTTS (Free, no API key)
# ====================================================================
# This file handles voice generation for medication summaries and alerts
# ====================================================================

from gtts import gTTS
import os
from datetime import datetime

# Create folder for audio files
AUDIO_CACHE_DIR = "audio_cache"
os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)


def text_to_speech_gtts(text, filename="complete_report.mp3"):
    """
    Convert text to speech using gTTS (Google Text-to-Speech)
    
    Args:
        text: The text to convert to speech
        filename: Output filename (will be saved in audio_cache folder)
    
    Returns:
        str: Full path to the generated audio file
    """
    if not text or text.strip() == "":
        print("⚠️ No text to convert to speech")
        return None
    
    # Add timestamp to filename to avoid caching issues
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{AUDIO_CACHE_DIR}/{timestamp}_{filename}"
    
    try:
        # Generate speech (slow=True is better for elderly users)
        tts = gTTS(text=text, lang='en', slow=True)
        tts.save(full_filename)
        print(f"✅ Voice report saved to: {full_filename}")
        return full_filename
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        return None


def text_to_speech_gtts_fast(text, filename="complete_report.mp3"):
    """
    Same as above but with normal speed (not slow)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{AUDIO_CACHE_DIR}/{timestamp}_{filename}"
    
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(full_filename)
        return full_filename
    except Exception as e:
        print(f"❌ Error generating speech: {e}")
        return None


def cleanup_old_audio_files(max_files=20):
    """
    Delete old audio files to save disk space
    Keeps only the most recent 'max_files' files
    """
    try:
        if not os.path.exists(AUDIO_CACHE_DIR):
            return
            
        files = [os.path.join(AUDIO_CACHE_DIR, f) for f in os.listdir(AUDIO_CACHE_DIR) 
                 if f.endswith('.mp3')]
        files.sort(key=os.path.getmtime, reverse=True)
        
        # Delete old files
        for old_file in files[max_files:]:
            os.remove(old_file)
            print(f"🗑️ Deleted old audio: {old_file}")
    except Exception as e:
        print(f"⚠️ Could not cleanup audio files: {e}")