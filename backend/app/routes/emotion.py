from fastapi import APIRouter, UploadFile, File, Form
from app.services.emotion_service import detect_emotion
from app.services.tutor_service import update_emotion

router = APIRouter()


@router.post("/detect-emotion")
async def detect_emotion_api(
    session_id: str = Form(...),
    file: UploadFile = File(...)
):
    frame_bytes = await file.read()

    emotion = detect_emotion(frame_bytes)

    update_emotion(session_id, emotion)

    return {
        "emotion": emotion
    }