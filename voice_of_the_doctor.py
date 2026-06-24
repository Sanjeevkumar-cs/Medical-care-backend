 # Use ElevenLabs for Text to Speech with Autoplay
import os
# from dotenv import load_dotenv
# load_dotenv()

from elevenlabs.client import ElevenLabs
# from playsound import playsound

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")

def text_to_speech_with_elevenlabs(input_text, output_filepath):
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    audio_stream = client.text_to_speech.convert(
        text=input_text,
        voice_id="FGY2WhTYpPnrIDTdsKH5",  # Replace with your desired voice ID
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )
    with open(output_filepath, "wb") as f:
        for chunk in audio_stream:
            if chunk:
                f.write(chunk)
    print(f"✅ Success! Audio saved to: {output_filepath}")


