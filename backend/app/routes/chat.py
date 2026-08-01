from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat import Chat
from app.models.schemas import ChatRequest
from app.models.chat_session import ChatSession

from fastapi.responses import StreamingResponse
import json

from app.services.llm_service import generate_reply, clean_text, generate_reply_stream
from app.services.tutor_service import start_study_session

router = APIRouter()

@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Generate AI response
    history = (
            db.query(Chat)
            .filter(Chat.session_id == request.session_id)
            .order_by(Chat.id.asc())
            .all()
        )

    messages = []

    for chat in history:
        messages.append({
            "role": "user",
            "content": chat.question
        })

        messages.append({
            "role": "assistant",
            "content": chat.answer
        })

    messages.append({
        "role": "user",
        "content": request.message
    })

    reply = generate_reply(
        messages,
        request.emotion
    )
    plain = clean_text(reply)

    # Save chat in database
    new_chat = Chat(
        user_id=current_user.id,
        session_id=request.session_id,
        question=request.message,
        answer=reply
    )

    session = db.query(ChatSession).filter(
        ChatSession.id == request.session_id
    ).first()

    if session and session.title == "New Chat":
        session.title = request.message[:50]

    db.add(new_chat)
    db.commit()

    # Existing study session logic
    study_session_id = str(uuid.uuid4())
    reading_time = start_study_session(study_session_id, plain)

    return {
        "reply": reply,
        "plain_text": plain,
        "emotion": request.emotion,
        "session_id": request.session_id,
        "study_session_id": study_session_id,
        "reading_time": reading_time
    }


@router.post("/chat-stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    history = (
        db.query(Chat)
        .filter(Chat.session_id == request.session_id)
        .order_by(Chat.id.asc())
        .all()
    )

    messages = []

    for chat in history:
        messages.append({
            "role": "user",
            "content": chat.question
        })

        messages.append({
            "role": "assistant",
            "content": chat.answer
        })

    messages.append({
        "role": "user",
        "content": request.message
    })

    def event_stream():

        full_reply = ""

        for token in generate_reply_stream(messages, request.emotion):

            full_reply += token

            yield json.dumps({
                "token": token
            }) + "\n"

        plain = clean_text(full_reply)

        new_chat = Chat(
            user_id=current_user.id,
            session_id=request.session_id,
            question=request.message,
            answer=plain
        )

        session = db.query(ChatSession).filter(
            ChatSession.id == request.session_id
        ).first()

        if session and session.title == "New Chat":
            session.title = request.message[:50]

        db.add(new_chat)
        db.commit()

        return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson"
    )