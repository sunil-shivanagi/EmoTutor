from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.learning_topic import LearningTopic

from app.services.game_service import (
    generate_hangman_words,
    generate_crossword_words
)


router = APIRouter()


# =========================================================
# GAME REQUEST
# =========================================================

class GameRequest(BaseModel):

    # Explicit topic is optional.
    # Usually the backend will determine the topic
    # from session_id / topic_id.
    topic: str | None = None

    # Current chat session
    session_id: int | None = None

    # Older stored learning topic
    topic_id: int | None = None

    # Whether PDF content should be used
    use_pdf: bool = True

    # Number of words
    num_words: int = 5


# =========================================================
# RESOLVE TOPIC
# =========================================================

def resolve_game_topic(
    request: GameRequest,
    db: Session,
    current_user: User
):

    selected_topic = None
    selected_pdf_id = None
    selected_topic_id = None

    # -----------------------------------------------------
    # 1. Explicit older topic
    # -----------------------------------------------------

    if request.topic_id is not None:

        topic_record = (
            db.query(LearningTopic)
            .filter(
                LearningTopic.id == request.topic_id,
                LearningTopic.user_id == current_user.id
            )
            .first()
        )

        if topic_record is None:

            raise HTTPException(
                status_code=404,
                detail="Learning topic not found."
            )

        selected_topic = topic_record.topic
        selected_pdf_id = topic_record.pdf_id
        selected_topic_id = topic_record.id

    # -----------------------------------------------------
    # 2. Current session topic
    # -----------------------------------------------------

    elif request.session_id is not None:

        session = (
            db.query(ChatSession)
            .filter(
                ChatSession.id == request.session_id,
                ChatSession.user_id == current_user.id
            )
            .first()
        )

        if session is None:

            raise HTTPException(
                status_code=404,
                detail="Chat session not found."
            )

        selected_pdf_id = session.pdf_id

        if session.current_topic_id is not None:

            topic_record = (
                db.query(LearningTopic)
                .filter(
                    LearningTopic.id == session.current_topic_id,
                    LearningTopic.user_id == current_user.id
                )
                .first()
            )

            if topic_record:

                selected_topic = topic_record.topic
                selected_pdf_id = topic_record.pdf_id
                selected_topic_id = topic_record.id

    # -----------------------------------------------------
    # 3. Explicit topic
    # -----------------------------------------------------

    if selected_topic is None and request.topic:

        selected_topic = request.topic.strip()

    # -----------------------------------------------------
    # 4. No topic
    # -----------------------------------------------------

    if not selected_topic:

        raise HTTPException(
            status_code=400,
            detail=(
                "No learning topic available. "
                "Please discuss a topic first."
            )
        )

    return (
        selected_topic,
        selected_topic_id,
        selected_pdf_id
    )


# =========================================================
# HANGMAN
# =========================================================

@router.post("/generate-hangman")
def hangman(
    request: GameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    (
        topic,
        topic_id,
        pdf_id
    ) = resolve_game_topic(
        request,
        db,
        current_user
    )

    use_pdf = (
        request.use_pdf
        and pdf_id is not None
    )

    print("=" * 60)
    print("HANGMAN REQUEST")
    print("Topic:", topic)
    print("Topic ID:", topic_id)
    print("Session ID:", request.session_id)
    print("PDF ID:", pdf_id)
    print("Use PDF:", use_pdf)
    print("Words:", request.num_words)
    print("=" * 60)

    words = generate_hangman_words(
        topic=topic,
        use_pdf=use_pdf,
        num_words=request.num_words,
        db=db,
        pdf_id=pdf_id
    )

    return {
        "words": words,
        "topic": topic,
        "topic_id": topic_id,
        "pdf_id": pdf_id
    }


# =========================================================
# CROSSWORD
# =========================================================

@router.post("/generate-crossword")
def crossword(
    request: GameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    (
        topic,
        topic_id,
        pdf_id
    ) = resolve_game_topic(
        request,
        db,
        current_user
    )

    use_pdf = (
        request.use_pdf
        and pdf_id is not None
    )

    print("=" * 60)
    print("CROSSWORD REQUEST")
    print("Topic:", topic)
    print("Topic ID:", topic_id)
    print("Session ID:", request.session_id)
    print("PDF ID:", pdf_id)
    print("Use PDF:", use_pdf)
    print("Words:", request.num_words)
    print("=" * 60)

    words = generate_crossword_words(
        topic=topic,
        use_pdf=use_pdf,
        num_words=request.num_words,
        db=db,
        pdf_id=pdf_id
    )

    return {
        "words": words,
        "topic": topic,
        "topic_id": topic_id,
        "pdf_id": pdf_id
    }