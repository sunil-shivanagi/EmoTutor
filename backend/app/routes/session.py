from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.chat import Chat

router = APIRouter(prefix="/session", tags=["Sessions"])


@router.post("/new")
def create_session(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    session = ChatSession(
        user_id=current_user.id,
        title="New Chat"
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "title": session.title
    }

@router.get("/list")
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sessions = (
        db.query(ChatSession)
        .filter(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at.strftime("%d %b %H:%M")
        }
        for s in sessions
    ]

@router.get("/{session_id}")
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    chats = (
        db.query(Chat)
        .filter(
            Chat.session_id == session_id,
            Chat.user_id == current_user.id
        )
        .order_by(Chat.created_at)
        .all()
    )

    return [
        {
            "question": chat.question,
            "answer": chat.answer
        }
        for chat in chats
    ]

@router.delete("/{session_id}")
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # Delete all messages in the session
    db.query(Chat).filter(
        Chat.session_id == session_id,
        Chat.user_id == current_user.id
    ).delete()

    # Delete the session
    db.query(ChatSession).filter(
        ChatSession.id == session_id,
        ChatSession.user_id == current_user.id
    ).delete()

    db.commit()

    return {"message": "Session deleted"}


@router.get("/search/{keyword}")
def search_sessions(
    keyword: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    sessions = (
        db.query(ChatSession)
        .outerjoin(Chat, Chat.session_id == ChatSession.id)
        .filter(
            ChatSession.user_id == current_user.id,
            or_(
                ChatSession.title.ilike(f"%{keyword}%"),
                Chat.question.ilike(f"%{keyword}%"),
                Chat.answer.ilike(f"%{keyword}%")
            )
        )
        .distinct()
        .order_by(ChatSession.created_at.desc())
        .all()
    )

    return sessions