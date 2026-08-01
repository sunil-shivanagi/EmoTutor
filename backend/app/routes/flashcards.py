from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat import Chat

from app.services.llm_service import generate_flashcards

router = APIRouter(
    prefix="/flashcards",
    tags=["Flashcards"]
)

@router.get("/{session_id}")
def flashcards(
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

    if not chats:
        return {
            "flashcards": []
        }

    conversation = ""

    for chat in chats:
        conversation += f"Student: {chat.question}\n"
        conversation += f"Tutor: {chat.answer}\n\n"

    cards = generate_flashcards(conversation)

    return {
        "flashcards": cards
    }