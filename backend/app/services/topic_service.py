from groq import Groq
from sqlalchemy.orm import Session
from sqlalchemy import func
import json
import re

from app.config import GROQ_API_KEY
from app.models.learning_topic import LearningTopic
from app.models.chat_session import ChatSession


client = Groq(api_key=GROQ_API_KEY)


# =========================================================
# TOPIC ANALYSIS
# =========================================================

def analyze_topic(
    message: str,
    history: list,
    current_topic: str | None,
    existing_topics: list[str],
    pdf_context: str = ""
) -> dict:

    previous_topics = "\n".join(
        f"- {topic}" for topic in existing_topics
    )

    conversation = ""

    for item in history:
        conversation += (
            f"Student: {item['question']}\n"
            f"Tutor: {item['answer']}\n\n"
        )

    prompt = f"""
You are the learning-topic analyzer for an AI tutoring system.

Your job is to determine whether the student's latest message
belongs to a learning topic.

You MUST NOT use hardcoded keyword rules.

Understand the meaning of the student's message using:
- conversation history
- current learning topic
- previously discussed topics
- PDF context when available

CURRENT TOPIC:
{current_topic or "None"}

PREVIOUSLY DISCUSSED TOPICS:
{previous_topics or "None"}

CONVERSATION HISTORY:
{conversation or "No previous conversation"}

PDF CONTEXT:
{pdf_context[:5000] if pdf_context else "No PDF context"}

LATEST STUDENT MESSAGE:
{message}

Determine exactly ONE action:

1. "none"
   Use when the message is casual conversation, greeting,
   thanks, unrelated chat, or does not establish a learning topic.

2. "continue"
   Use when the student is continuing the current learning topic.
   This includes messages such as asking for examples, explanation,
   clarification, practice questions, summaries, etc.

3. "new"
   Use when the student has clearly started learning a new topic.

4. "existing"
   Use when the student is returning to a previously discussed topic.

IMPORTANT:

- Do NOT create a topic from casual conversation.
- Do NOT treat "quiz", "game", "test", "practice", "examples",
  "explain again", "continue", etc. as topics by themselves.
- If the student asks for a quiz/game/practice and there is a current
  topic, use "continue" and keep the current topic.
- If the student refers to "that topic", "previous topic",
  "the first one", "what we discussed earlier", etc., use the
  conversation and topic history to determine the correct topic.
- Topic names should be concise and educational.
- Do not create duplicate topic names.
- If a new topic is a subtopic of the current topic, use the more
  specific educational topic.
- The topic should describe WHAT the student is learning,
  not WHAT they are asking the tutor to do.

Return ONLY valid JSON:

{{
    "action": "none|continue|new|existing",
    "topic": "topic name or null",
    "confidence": 0.0
}}

Examples:

Student: "Hi"
→ {{"action":"none","topic":null,"confidence":0.99}}

Student: "What is a chemical reaction?"
→ {{"action":"new","topic":"Chemical Reactions","confidence":0.98}}

Student: "Give me examples"
Current topic: "Chemical Reactions"
→ {{"action":"continue","topic":"Chemical Reactions","confidence":0.97}}

Student: "Explain displacement reaction"
Current topic: "Chemical Reactions"
→ {{"action":"new","topic":"Displacement Reactions","confidence":0.96}}

Student: "Give me a quiz"
Current topic: "Displacement Reactions"
→ {{"action":"continue","topic":"Displacement Reactions","confidence":0.99}}

Student: "What about decomposition?"
Current topic: "Displacement Reactions"
→ {{"action":"new","topic":"Decomposition Reactions","confidence":0.96}}
"""

    try:

        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise educational topic "
                        "classification system. Return only JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.1,
            max_tokens=300
        )

        raw = response.choices[0].message.content.strip()

        raw = re.sub(
            r"```json|```",
            "",
            raw
        ).strip()

        result = json.loads(raw)

        action = result.get("action", "none")
        topic = result.get("topic")
        confidence = float(
            result.get("confidence", 0)
        )

        if action not in {
            "none",
            "continue",
            "new",
            "existing"
        }:
            action = "none"

        if not topic or not isinstance(topic, str):
            topic = None

        return {
            "action": action,
            "topic": topic.strip() if topic else None,
            "confidence": confidence
        }

    except Exception as e:

        print(
            "Topic analysis error:",
            e
        )

        return {
            "action": "none",
            "topic": None,
            "confidence": 0.0
        }


# =========================================================
# UPDATE / CREATE TOPIC
# =========================================================

def update_learning_topic(
    db: Session,
    session: ChatSession,
    analysis: dict
) -> LearningTopic | None:

    action = analysis.get("action")
    topic_name = analysis.get("topic")

    # -----------------------------------------------------
    # No learning topic
    # -----------------------------------------------------

    if action == "none" or not topic_name:
        return get_current_topic(
            db,
            session
        )

    # -----------------------------------------------------
    # Normalize topic for duplicate checking
    # -----------------------------------------------------

    normalized_topic = topic_name.strip()

    # -----------------------------------------------------
    # Look for existing topic in THIS session
    # -----------------------------------------------------

    existing = (
        db.query(LearningTopic)
        .filter(
            LearningTopic.session_id == session.id,
            func.lower(
                LearningTopic.topic
            ) == normalized_topic.lower()
        )
        .first()
    )

    # -----------------------------------------------------
    # Existing topic
    # -----------------------------------------------------

    if existing:

        existing.last_discussed_at = func.now()
        existing.discussion_count += 1

        session.current_topic_id = existing.id

        db.commit()
        db.refresh(existing)

        return existing

    # -----------------------------------------------------
    # Create new topic
    # -----------------------------------------------------

    new_topic = LearningTopic(
        session_id=session.id,
        user_id=session.user_id,
        pdf_id=session.pdf_id,
        topic=normalized_topic,
        discussion_count=1
    )

    db.add(new_topic)
    db.flush()

    session.current_topic_id = new_topic.id

    db.commit()
    db.refresh(new_topic)

    print(
        "New learning topic:",
        new_topic.topic
    )

    return new_topic


# =========================================================
# GET CURRENT TOPIC
# =========================================================

def get_current_topic(
    db: Session,
    session: ChatSession
) -> LearningTopic | None:

    if session.current_topic_id is None:
        return None

    return (
        db.query(LearningTopic)
        .filter(
            LearningTopic.id ==
            session.current_topic_id
        )
        .first()
    )


# =========================================================
# GET ALL SESSION TOPICS
# =========================================================

def get_session_topics(
    db: Session,
    session_id: int,
    user_id: int
) -> list[LearningTopic]:

    return (
        db.query(LearningTopic)
        .filter(
            LearningTopic.session_id == session_id,
            LearningTopic.user_id == user_id
        )
        .order_by(
            LearningTopic.first_discussed_at.asc()
        )
        .all()
    )