from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.chat import Chat
from app.models.pdf import PDF
from app.models.learning_topic import LearningTopic


router = APIRouter(
    prefix="/session",
    tags=["Sessions"]
)


# =========================================================
# CREATE SESSION REQUEST
# =========================================================

class CreateSessionRequest(BaseModel):
    pdf_id: int | None = None


# =========================================================
# CREATE NEW SESSION
# =========================================================

@router.post("/new")
def create_session(
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # If a PDF was provided, verify that it belongs
    # to the current user
    # -----------------------------------------------------

    if request.pdf_id is not None:

        pdf = (
            db.query(PDF)
            .filter(
                PDF.id == request.pdf_id,
                PDF.user_id == current_user.id
            )
            .first()
        )

        if pdf is None:
            raise HTTPException(
                status_code=404,
                detail="PDF not found."
            )

    # -----------------------------------------------------
    # Create session
    # -----------------------------------------------------

    session = ChatSession(
        user_id=current_user.id,
        pdf_id=request.pdf_id,
        current_topic_id=None,
        title="New Chat"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    print(
        "Created session:",
        session.id,
        "PDF:",
        session.pdf_id
    )

    return {
        "session_id": session.id,
        "title": session.title,
        "pdf_id": session.pdf_id,
        "current_topic": None
    }


# =========================================================
# LIST USER SESSIONS
# =========================================================

@router.get("/list")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sessions = (
        db.query(ChatSession)
        .filter(
            ChatSession.user_id == current_user.id
        )
        .order_by(
            ChatSession.created_at.desc()
        )
        .all()
    )

    result = []

    for session in sessions:

        current_topic = None

        if session.current_topic_id is not None:

            topic = (
                db.query(LearningTopic)
                .filter(
                    LearningTopic.id == session.current_topic_id,
                    LearningTopic.user_id == current_user.id
                )
                .first()
            )

            if topic:
                current_topic = {
                    "id": topic.id,
                    "topic": topic.topic
                }

        result.append({
            "id": session.id,
            "title": session.title,
            "pdf_id": session.pdf_id,
            "current_topic": current_topic,
            "created_at": (
                session.created_at.strftime(
                    "%d %b %H:%M"
                )
                if session.created_at
                else None
            )
        })

    return result


# =========================================================
# GET ONE SESSION + MESSAGES + TOPICS
# =========================================================

@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # Get session
    # -----------------------------------------------------

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    # -----------------------------------------------------
    # Get chats
    # -----------------------------------------------------

    chats = (
        db.query(Chat)
        .filter(
            Chat.session_id == session_id,
            Chat.user_id == current_user.id
        )
        .order_by(
            Chat.created_at.asc()
        )
        .all()
    )

    # -----------------------------------------------------
    # PDF information
    # -----------------------------------------------------

    pdf_data = None

    if session.pdf_id is not None:

        pdf = (
            db.query(PDF)
            .filter(
                PDF.id == session.pdf_id,
                PDF.user_id == current_user.id
            )
            .first()
        )

        if pdf:

            pdf_data = {
                "id": pdf.id,
                "filename": pdf.filename
            }

    # -----------------------------------------------------
    # Get all learning topics for this session
    # -----------------------------------------------------

    topics = (
        db.query(LearningTopic)
        .filter(
            LearningTopic.session_id == session_id,
            LearningTopic.user_id == current_user.id
        )
        .order_by(
            LearningTopic.last_discussed_at.desc()
        )
        .all()
    )

    topic_data = [
        {
            "id": topic.id,
            "topic": topic.topic,
            "pdf_id": topic.pdf_id,
            "discussion_count": topic.discussion_count,
            "first_discussed_at": topic.first_discussed_at,
            "last_discussed_at": topic.last_discussed_at,
            "is_current": (
                topic.id == session.current_topic_id
            )
        }
        for topic in topics
    ]

    # -----------------------------------------------------
    # Current topic
    # -----------------------------------------------------

    current_topic_data = None

    if session.current_topic_id is not None:

        current_topic = (
            db.query(LearningTopic)
            .filter(
                LearningTopic.id == session.current_topic_id,
                LearningTopic.session_id == session_id,
                LearningTopic.user_id == current_user.id
            )
            .first()
        )

        if current_topic:

            current_topic_data = {
                "id": current_topic.id,
                "topic": current_topic.topic,
                "pdf_id": current_topic.pdf_id,
                "discussion_count": current_topic.discussion_count
            }

    # -----------------------------------------------------
    # Return session
    # -----------------------------------------------------

    return {
        "session_id": session.id,
        "title": session.title,

        "pdf": pdf_data,

        # Current topic used for things like
        # automatic quiz/game suggestions
        "current_topic": current_topic_data,

        # All topics discussed in this session
        "topics": topic_data,

        # Chat history
        "messages": [
            {
                "question": chat.question,
                "answer": chat.answer,
                "created_at": chat.created_at
            }
            for chat in chats
        ]
    }


# =========================================================
# GET TOPICS FOR A SESSION
# =========================================================

@router.get("/{session_id}/topics")
def get_session_topics(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # Verify session belongs to user
    # -----------------------------------------------------

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    # -----------------------------------------------------
    # Get topics
    # -----------------------------------------------------

    topics = (
        db.query(LearningTopic)
        .filter(
            LearningTopic.session_id == session_id,
            LearningTopic.user_id == current_user.id
        )
        .order_by(
            LearningTopic.last_discussed_at.desc()
        )
        .all()
    )

    # -----------------------------------------------------
    # Return topics
    # -----------------------------------------------------

    return {
        "session_id": session.id,

        "current_topic_id": session.current_topic_id,

        "topics": [
            {
                "id": topic.id,
                "topic": topic.topic,
                "pdf_id": topic.pdf_id,
                "discussion_count": topic.discussion_count,
                "is_current": (
                    topic.id == session.current_topic_id
                )
            }
            for topic in topics
        ]
    }


# =========================================================
# DELETE SESSION
# =========================================================

@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # Verify session belongs to user
    # -----------------------------------------------------

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found."
        )

    # -----------------------------------------------------
    # Delete messages
    # -----------------------------------------------------

    db.query(Chat).filter(
        Chat.session_id == session_id,
        Chat.user_id == current_user.id
    ).delete(
        synchronize_session=False
    )

    # -----------------------------------------------------
    # Delete session
    #
    # learning_topics will be deleted automatically
    # because its FK uses ON DELETE CASCADE.
    # -----------------------------------------------------

    db.delete(session)

    db.commit()

    return {
        "message": "Session deleted"
    }


# =========================================================
# SEARCH SESSIONS
# =========================================================

@router.get("/search/{keyword}")
def search_sessions(
    keyword: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sessions = (
        db.query(ChatSession)
        .outerjoin(
            Chat,
            Chat.session_id == ChatSession.id
        )
        .filter(
            ChatSession.user_id == current_user.id,
            or_(
                ChatSession.title.ilike(
                    f"%{keyword}%"
                ),
                Chat.question.ilike(
                    f"%{keyword}%"
                ),
                Chat.answer.ilike(
                    f"%{keyword}%"
                )
            )
        )
        .distinct()
        .order_by(
            ChatSession.created_at.desc()
        )
        .all()
    )

    return [
        {
            "id": session.id,
            "title": session.title,
            "pdf_id": session.pdf_id,
            "created_at": (
                session.created_at.strftime(
                    "%d %b %H:%M"
                )
                if session.created_at
                else None
            )
        }
        for session in sessions
    ]