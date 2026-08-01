"""from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.services.tts_service import text_to_speech

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@router.post("/tts")
def tts(request: TTSRequest):
    audio_bytes = text_to_speech(request.text)
    
    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg"
    )
"""

"""
from fastapi import APIRouter
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid
import os

from app.services.tts_service import text_to_speech

router = APIRouter()

# Request model
class TTSRequest(BaseModel):
    text: str

@router.post("/tts")
def tts(request: TTSRequest):
    # 🔊 Generate audio bytes from text
    audio_bytes = text_to_speech(request.text)

    # 📁 Create folder if it doesn't exist
    os.makedirs("audio", exist_ok=True)

    # 🆔 Unique filename (prevents overwrite)
    filename = f"tts_{uuid.uuid4().hex}.mp3"
    filepath = os.path.join("audio", filename)

    # 💾 Save audio to file
    with open(filepath, "wb") as f:
        f.write(audio_bytes)

    # 🎧 Return audio file to client
    return FileResponse(
        path=filepath,
        media_type="audio/mpeg",
        filename=filename
    )
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

from app.services.tts_service import text_to_speech

router = APIRouter()

class TTSRequest(BaseModel):
    text: str

@router.post("/tts")
def tts(request: TTSRequest):
    audio_bytes = text_to_speech(request.text)

    return StreamingResponse(
        io.BytesIO(audio_bytes),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=tts.mp3"
        }
    )