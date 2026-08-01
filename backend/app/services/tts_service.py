import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("ELEVENLABS_API_KEY")

def text_to_speech(text: str) -> bytes:

    url = "https://api.elevenlabs.io/v1/text-to-speech/EXAVITQu4vr4xnSDxMaL"

    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, json=data, headers=headers)

    print("Status Code:", response.status_code)
    print("Content Length:", len(response.content))
    #print("Response Text:", response.text[:200])
    print("Audio received successfully")
    #if response.status_code != 200:
        #return b""
    if response.status_code != 200:
        raise Exception(response.text)

    return response.content