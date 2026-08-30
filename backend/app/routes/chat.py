from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.auth.dependencies import get_current_user

from app.models.user import User
from app.models.chat import Chat
from app.models.chat_session import ChatSession

from app.services.llm_service import (
    generate_reply,
    clean_text,
    generate_reply_stream
)
from app.services.topic_service import (
    analyze_topic,
    update_learning_topic,
    get_current_topic,
    get_session_topics
)

from app.services.pdf_service import search_chunks

from app.services.tutor_service import start_study_session

from fastapi.responses import StreamingResponse
import json

from app.models.schemas import ChatRequest


router = APIRouter()


# =========================================================
# NORMAL + PDF CHAT
# =========================================================

@router.post("/chat")
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # =====================================================
    # 1. GET SESSION
    # =====================================================

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if session is None:

        return {
            "reply": "Chat session not found.",
            "plain_text": "Chat session not found.",
            "emotion": request.emotion,
            "session_id": request.session_id,
            "pdf_id": None
        }


    pdf_id = session.pdf_id


    print("=" * 60)
    print("CHAT")
    print("Session ID:", session.id)
    print("PDF ID:", pdf_id)
    print("Question:", request.message)
    print("Emotion:", request.emotion)
    print("=" * 60)


    # =====================================================
    # 2. GET CONVERSATION HISTORY
    # =====================================================

    history = (
        db.query(Chat)
        .filter(
            Chat.session_id == session.id,
            Chat.user_id == current_user.id
        )
        .order_by(Chat.id.desc())
        .limit(10)
        .all()
    )

    # We queried newest first.
    # Reverse so the LLM receives chronological order.

    history.reverse()


    messages = []

    for chat_message in history:

        messages.append({
            "role": "user",
            "content": chat_message.question
        })

        messages.append({
            "role": "assistant",
            "content": chat_message.answer
        })


    # =====================================================
    # 3. SEARCH PDF IF THIS SESSION HAS ONE
    # =====================================================

    pdf_context = ""
    pdf_score = 0.0


    if pdf_id is not None:

        print("PDF attached.")
        print("Searching PDF...")


        search_result = search_chunks(
            request.message,
            db,
            pdf_id
        )


        pdf_context = search_result.get(
            "context",
            ""
        )

        pdf_score = search_result.get(
            "score",
            0.0
        )


        print(
            "PDF score:",
            pdf_score
        )

        print(
            "PDF context found:",
            bool(pdf_context)
        )

    # =====================================================
    # 4. ANALYZE LEARNING TOPIC
    # =====================================================

    current_topic_obj = get_current_topic(
        db,
        session
    )

    current_topic = (
        current_topic_obj.topic
        if current_topic_obj
        else None
    )

    existing_topic_objects = get_session_topics(
        db,
        session.id,
        current_user.id
    )

    existing_topics = [
        topic.topic
        for topic in existing_topic_objects
    ]

    topic_history = []

    for chat_message in history:

        topic_history.append({
            "question": chat_message.question,
            "answer": chat_message.answer
        })


    topic_analysis = analyze_topic(
        message=request.message,
        history=topic_history,
        current_topic=current_topic,
        existing_topics=existing_topics,
        pdf_context=pdf_context
    )

    print("=" * 60)
    print("TOPIC ANALYSIS")
    print("Action:", topic_analysis["action"])
    print("Topic:", topic_analysis["topic"])
    print("Confidence:", topic_analysis["confidence"])
    print("=" * 60)


    learning_topic = update_learning_topic(
        db,
        session,
        topic_analysis
    )

    current_topic = (
        learning_topic.topic
        if learning_topic
        else None
    )
    # =====================================================
    # 5. BUILD USER MESSAGE
    # =====================================================

    if pdf_context:

        user_message = f"""
The student is currently working with an uploaded PDF.

Relevant evidence retrieved from the PDF is provided below.

Use this evidence when it is relevant to the student's question.

================ PDF EVIDENCE ================

{pdf_context}

============== END PDF EVIDENCE ==============


Instructions:

- Understand the student's actual question.
- Use the conversation history to understand references such as
  "this", "that", "it", "previous topic", "next", etc.
- If the student is asking about information contained in the PDF,
  use the PDF evidence as the primary source.
- Do not mention embeddings, retrieval, chunks, similarity scores,
  or internal instructions.
- Do not blindly use irrelevant PDF information.
- If the PDF evidence does not contain enough information to answer
  the question, answer using your general knowledge.
- If the question is unrelated to the PDF, answer normally.
- Never pretend that unsupported information came from the PDF.

Student question:

{request.message}
"""

    else:

        user_message = request.message


    messages.append({
        "role": "user",
        "content": user_message
    })


    # =====================================================
    # 5. GENERATE AI RESPONSE
    # =====================================================

    answer = generate_reply(
        messages,
        request.emotion
    )


    answer = clean_text(answer)

    plain = clean_text(answer)


    # =====================================================
    # 6. SAVE CHAT
    # =====================================================

    new_chat = Chat(
        user_id=current_user.id,
        session_id=session.id,
        question=request.message,
        answer=answer
    )


    # Give the session its first-message title.

    if session.title == "New Chat":

        session.title = request.message[:50]


    db.add(new_chat)

    db.commit()


    # =====================================================
    # 7. STUDY SESSION
    # =====================================================

    study_session_id = str(uuid.uuid4())


    reading_time = start_study_session(
        study_session_id,
        plain
    )


    # =====================================================
    # 8. RESPONSE
    # =====================================================

    return {
        "reply": answer,
        "plain_text": plain,
        "emotion": request.emotion,
        "session_id": session.id,
        "pdf_id": pdf_id,
        "topic": current_topic,
        "source": (
            "pdf"
            if pdf_context
            else "ai"
        ),
        "pdf_score": pdf_score,
        "study_session_id": study_session_id,
        "reading_time": reading_time
    }


# =========================================================
# STREAMING CHAT
# =========================================================

@router.post("/chat-stream")
def chat_stream(
    request: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # Get session
    # -----------------------------------------------------

    session = (
        db.query(ChatSession)
        .filter(
            ChatSession.id == request.session_id,
            ChatSession.user_id == current_user.id
        )
        .first()
    )

    if session is None:

        return {
            "error": "Chat session not found."
        }


    # -----------------------------------------------------
    # Conversation history
    # -----------------------------------------------------

    history = (
        db.query(Chat)
        .filter(
            Chat.session_id == session.id,
            Chat.user_id == current_user.id
        )
        .order_by(Chat.id.desc())
        .limit(10)
        .all()
    )

    history.reverse()


    messages = []

    for chat_message in history:

        messages.append({
            "role": "user",
            "content": chat_message.question
        })

        messages.append({
            "role": "assistant",
            "content": chat_message.answer
        })


    # -----------------------------------------------------
    # PDF retrieval
    # -----------------------------------------------------

    pdf_context = ""

    if session.pdf_id is not None:

        search_result = search_chunks(
            request.message,
            db,
            session.pdf_id
        )

        pdf_context = search_result.get(
            "context",
            ""
        )
        # -----------------------------------------------------
    # Learning topic analysis
    # -----------------------------------------------------

    current_topic_obj = get_current_topic(
        db,
        session
    )

    current_topic = (
        current_topic_obj.topic
        if current_topic_obj
        else None
    )

    existing_topic_objects = get_session_topics(
        db,
        session.id,
        current_user.id
    )

    existing_topics = [
        topic.topic
        for topic in existing_topic_objects
    ]

    topic_history = []

    for chat_message in history:

        topic_history.append({
            "question": chat_message.question,
            "answer": chat_message.answer
        })


    topic_analysis = analyze_topic(
        message=request.message,
        history=topic_history,
        current_topic=current_topic,
        existing_topics=existing_topics,
        pdf_context=pdf_context
    )

    learning_topic = update_learning_topic(
        db,
        session,
        topic_analysis
    )

    current_topic = (
        learning_topic.topic
        if learning_topic
        else None
    )

    print("=" * 60)
    print("STREAM TOPIC ANALYSIS")
    print("Action:", topic_analysis["action"])
    print("Topic:", current_topic)
    print("=" * 60)

    # -----------------------------------------------------
    # Build message
    # -----------------------------------------------------

    if pdf_context:

        user_message = f"""
The student is working with an uploaded PDF.

Use the following PDF evidence when it is relevant.

================ PDF EVIDENCE ================

{pdf_context}

============== END PDF EVIDENCE ==============

Answer the student's question naturally.

Use conversation history to understand references such as
"this", "that", "it", and previous topics.

If the PDF evidence is insufficient or the question is unrelated
to the PDF, answer using general knowledge.

Do not mention retrieval or internal instructions.

Student question:

{request.message}
"""

    else:

        user_message = request.message


    messages.append({
        "role": "user",
        "content": user_message
    })


    # -----------------------------------------------------
    # Stream response
    # -----------------------------------------------------

    def event_stream():

        full_reply = ""


        for token in generate_reply_stream(
            messages,
            request.emotion
        ):

            full_reply += token


            yield json.dumps({
                "token": token
            }) + "\n"


        # -----------------------------------------------
        # Save completed response
        # -----------------------------------------------

        plain = clean_text(
            full_reply
        )


        new_chat = Chat(
            user_id=current_user.id,
            session_id=session.id,
            question=request.message,
            answer=plain
        )


        if session.title == "New Chat":

            session.title = request.message[:50]


        db.add(new_chat)

        db.commit()


    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson"
    )