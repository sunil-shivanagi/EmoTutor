from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat_session import ChatSession
from app.models.learning_topic import LearningTopic

from app.services.quiz_service import generate_quiz


router = APIRouter()


# =========================================================
# QUIZ REQUEST
# =========================================================

class QuizRequest(BaseModel):

    # Optional because the backend can determine
    # the topic from session_id / topic_id.
    topic: str | None = None

    quiz_type: str = "mcq"

    num_questions: int = 5

    use_pdf: bool = True

    # Current chat session
    session_id: int | None = None

    # Older topic selected by the student
    topic_id: int | None = None


# =========================================================
# GENERATE QUIZ
# =========================================================

@router.post("/generate-quiz")
def generate_quiz_route(
    request: QuizRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # Validate number of questions
    # -----------------------------------------------------

    if request.num_questions < 1:
        raise HTTPException(
            status_code=400,
            detail="Number of questions must be at least 1."
        )

    if request.num_questions > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 questions allowed."
        )

    # -----------------------------------------------------
    # Find topic
    # -----------------------------------------------------

    selected_topic = None
    selected_pdf_id = None
    selected_topic_id = None

    # =====================================================
    # CASE 1
    # topic_id supplied
    #
    # Used when student chooses an older topic.
    # =====================================================

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

    # =====================================================
    # CASE 2
    # session_id supplied
    #
    # Used for the current topic.
    # =====================================================

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

        # Current topic of this session
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
                selected_topic_id = topic_record.id

    # =====================================================
    # CASE 3
    # Explicit topic supplied
    # =====================================================

    if selected_topic is None and request.topic:

        selected_topic = request.topic.strip()

    # =====================================================
    # NO TOPIC
    # =====================================================

    if not selected_topic:

        raise HTTPException(
            status_code=400,
            detail=(
                "No learning topic available. "
                "Please discuss a topic first."
            )
        )

    # =====================================================
    # PDF
    #
    # Topic may have its own PDF.
    # Otherwise use the session PDF.
    # =====================================================

    if selected_topic_id is not None:

        topic_record = (
            db.query(LearningTopic)
            .filter(
                LearningTopic.id == selected_topic_id,
                LearningTopic.user_id == current_user.id
            )
            .first()
        )

        if topic_record:

            selected_pdf_id = topic_record.pdf_id

    # =====================================================
    # Generate quiz
    # =====================================================

    print("=" * 60)
    print("QUIZ REQUEST")
    print("Topic:", selected_topic)
    print("Topic ID:", selected_topic_id)
    print("Session ID:", request.session_id)
    print("PDF ID:", selected_pdf_id)
    print("Quiz type:", request.quiz_type)
    print("Questions:", request.num_questions)
    print("=" * 60)

    quiz = generate_quiz(
        topic=selected_topic,
        quiz_type=request.quiz_type,
        num_questions=request.num_questions,
        use_pdf=(
            request.use_pdf
            and selected_pdf_id is not None
        ),
        pdf_id=selected_pdf_id,
        db=db
    )

    # =====================================================
    # RESPONSE
    # =====================================================

    return {
        "quiz": quiz,
        "topic": selected_topic,
        "topic_id": selected_topic_id,
        "pdf_id": selected_pdf_id
    }