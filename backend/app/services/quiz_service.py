from app.services.pdf_service import search_chunks
from app.config import GROQ_API_KEY
from groq import Groq
import json
import re

client = Groq(api_key=GROQ_API_KEY)


def get_format_instructions(quiz_type: str, num_questions: int) -> str:

    num = str(num_questions)

    if quiz_type == "mcq":
        return f"""
Generate exactly {num} multiple choice questions.
Return ONLY a JSON array like this:
[
  {{
    "type": "mcq",
    "question": "Question here?",
    "options": {{"A": "option1", "B": "option2", "C": "option3", "D": "option4"}},
    "answer": "A"
  }}
]"""

    elif quiz_type == "truefalse":
        return f"""
Generate exactly {num} true/false questions.
Return ONLY a JSON array like this:
[
  {{
    "type": "truefalse",
    "question": "Statement here.",
    "answer": "True"
  }}
]"""

    elif quiz_type == "shortanswer":
        return f"""
Generate exactly {num} short answer questions.
Return ONLY a JSON array like this:
[
  {{
    "type": "shortanswer",
    "question": "Question here?",
    "answer": "Expected answer here"
  }}
]"""

    else:  # mix
        return f"""
Generate exactly {num} mixed questions (mix of mcq, truefalse, shortanswer).
Return ONLY a JSON array like this:
[
  {{
    "type": "mcq",
    "question": "Question?",
    "options": {{"A": "opt1", "B": "opt2", "C": "opt3", "D": "opt4"}},
    "answer": "A"
  }},
  {{
    "type": "truefalse",
    "question": "Statement.",
    "answer": "True"
  }},
  {{
    "type": "shortanswer",
    "question": "Question?",
    "answer": "Answer"
  }}
]"""


def call_llm(prompt: str) -> list:
    """Call Groq and return parsed JSON list"""
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a quiz generator. Return only valid JSON arrays."},
                {"role": "user",   "content": prompt}
            ],
            temperature=0.7
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)

    except Exception as e:
        print("Quiz generation error:", e)
        return []


def generate_quiz(topic: str, quiz_type: str, num_questions: int, use_pdf: bool = True):

    # ── PDF mode ──────────────────────────────────────────────
    if use_pdf:
        from app.services.pdf_service import chunks as pdf_chunks

        if pdf_chunks and len(pdf_chunks) > 0:

            if topic:
                # Student was learning a specific topic → search PDF for it
                context = search_chunks(topic)
            else:
                # No specific topic → use broad PDF content
                context = " ".join(pdf_chunks[:6])[:3000]

            if context and len(context.strip()) > 50:
                prompt = f"""
You are a quiz generator for students.

Content from PDF:
{context}

{get_format_instructions(quiz_type, num_questions)}

IMPORTANT:
- Return ONLY the JSON array
- No extra text, no explanation, no markdown
- Base ALL questions strictly on the PDF content above
"""
                return call_llm(prompt)

    # ── Chat topic / General knowledge mode ───────────────────
    if not topic:
        topic = "general knowledge"

    context = f"General knowledge about: {topic}"

    prompt = f"""
You are a quiz generator for students.

Topic: {topic}

{get_format_instructions(quiz_type, num_questions)}

IMPORTANT:
- Return ONLY the JSON array
- No extra text, no explanation, no markdown
- Base questions on the topic
"""
    return call_llm(prompt)