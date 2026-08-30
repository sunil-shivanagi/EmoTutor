from app.services.pdf_service import search_chunks
from app.config import GROQ_API_KEY

from groq import Groq

from sqlalchemy.orm import Session

import json
import re


client = Groq(api_key=GROQ_API_KEY)


# =========================================================
# FORMAT INSTRUCTIONS
# =========================================================

def get_format_instructions(
    quiz_type: str,
    num_questions: int
) -> str:

    if quiz_type == "mcq":

        return f"""
Generate exactly {num_questions} multiple choice questions.

Return ONLY a JSON array:

[
  {{
    "type": "mcq",
    "question": "Question here?",
    "options": {{
      "A": "option1",
      "B": "option2",
      "C": "option3",
      "D": "option4"
    }},
    "answer": "A"
  }}
]
"""

    elif quiz_type == "truefalse":

        return f"""
Generate exactly {num_questions} true/false questions.

Return ONLY a JSON array:

[
  {{
    "type": "truefalse",
    "question": "Statement here.",
    "answer": "True"
  }}
]
"""

    elif quiz_type == "shortanswer":

        return f"""
Generate exactly {num_questions} short answer questions.

Return ONLY a JSON array:

[
  {{
    "type": "shortanswer",
    "question": "Question here?",
    "answer": "Expected answer here"
  }}
]
"""

    else:

        return f"""
Generate exactly {num_questions} mixed questions.

Mix:
- mcq
- truefalse
- shortanswer

Return ONLY a JSON array.

Each object must contain the correct fields
for its question type.
"""


# =========================================================
# CALL GROQ
# =========================================================

def call_llm(prompt: str) -> list:

    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert educational quiz "
                        "generator. Return ONLY valid JSON."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.5,

            max_tokens=1500
        )

        raw = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        # Remove markdown fences
        raw = re.sub(
            r"```json|```",
            "",
            raw
        ).strip()

        quiz = json.loads(raw)

        if not isinstance(quiz, list):

            print(
                "Quiz error: "
                "LLM did not return a JSON list."
            )

            return []

        return quiz

    except Exception as e:

        print(
            "Quiz generation error:",
            e
        )

        return []


# =========================================================
# GENERATE QUIZ
# =========================================================

def generate_quiz(
    topic: str,
    quiz_type: str,
    num_questions: int,
    use_pdf: bool = False,
    pdf_id: int | None = None,
    db: Session | None = None
) -> list:

    # -----------------------------------------------------
    # Validate topic
    # -----------------------------------------------------

    if not topic or not topic.strip():

        return []

    topic = topic.strip()

    # -----------------------------------------------------
    # Validate question count
    # -----------------------------------------------------

    num_questions = max(
        1,
        min(num_questions, 20)
    )

    context = ""

    # =====================================================
    # PDF MODE
    # =====================================================

    if (
        use_pdf
        and pdf_id is not None
        and db is not None
    ):

        print("=" * 60)
        print("QUIZ PDF SEARCH")
        print("Topic:", topic)
        print("PDF ID:", pdf_id)
        print("=" * 60)

        search_result = search_chunks(
            topic,
            db,
            pdf_id
        )

        context = search_result.get(
            "context",
            ""
        )

        print(
            "Quiz PDF relevance:",
            search_result.get("score", 0)
        )

        # -------------------------------------------------
        # PDF context found
        # -------------------------------------------------

        if context and len(context.strip()) > 50:

            prompt = f"""
You are an expert educational quiz generator.

The student is currently learning:

{topic}

The following information was retrieved from
the student's selected PDF.

PDF CONTENT:

{context}

{get_format_instructions(
    quiz_type,
    num_questions
)}

IMPORTANT RULES:

1. Generate exactly {num_questions} questions.

2. Every question must be specifically about:
   {topic}

3. Use the PDF content as the primary source.

4. Do NOT create questions from unrelated parts
   of the PDF.

5. Do NOT invent information that contradicts
   the PDF.

6. Questions should test understanding, not just
   memorization whenever possible.

7. Make questions suitable for a student.

8. Return ONLY the JSON array.

9. Do NOT return markdown.

10. Do NOT return explanations outside the JSON.
"""

            return call_llm(prompt)

    # =====================================================
    # GENERAL TOPIC MODE
    # =====================================================

    prompt = f"""
You are an expert educational quiz generator.

The student is currently learning:

{topic}

Generate a quiz specifically about:

{topic}

{get_format_instructions(
    quiz_type,
    num_questions
)}

IMPORTANT RULES:

1. Generate exactly {num_questions} questions.

2. Every question must be directly related to:
   {topic}

3. Test actual understanding.

4. Avoid repetitive questions.

5. Avoid questions about unrelated topics.

6. Return ONLY the JSON array.

7. Do NOT return markdown.

8. Do NOT return explanations outside the JSON.
"""

    return call_llm(prompt)