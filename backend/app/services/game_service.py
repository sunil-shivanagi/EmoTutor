from app.services.pdf_service import search_chunks
from app.config import GROQ_API_KEY

from groq import Groq
from sqlalchemy.orm import Session

import json
import re


client = Groq(api_key=GROQ_API_KEY)


# =========================================================
# CALL LLM
# =========================================================

def call_llm(prompt: str) -> list:

    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert educational "
                        "word game generator. "
                        "Return ONLY valid JSON arrays."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],

            temperature=0.5,

            max_tokens=1200
        )

        raw = (
            response
            .choices[0]
            .message
            .content
            .strip()
        )

        raw = re.sub(
            r"```json|```",
            "",
            raw
        ).strip()

        result = json.loads(raw)

        if not isinstance(result, list):

            print(
                "Game generation returned "
                "non-list response."
            )

            return []

        return result

    except Exception as e:

        print(
            "Game generation error:",
            e
        )

        return []


# =========================================================
# GET CONTEXT
# =========================================================

def get_context(
    topic: str,
    use_pdf: bool,
    db: Session | None = None,
    pdf_id: int | None = None
) -> str:

    # -----------------------------------------------------
    # PDF context
    # -----------------------------------------------------

    if (
        use_pdf
        and db is not None
        and pdf_id is not None
    ):

        print("=" * 60)
        print("GAME PDF SEARCH")
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
            "Game PDF relevance:",
            search_result.get(
                "score",
                0
            )
        )

        if (
            context
            and len(context.strip()) > 50
        ):

            return context

    # -----------------------------------------------------
    # General topic
    # -----------------------------------------------------

    return (
        f"General educational knowledge "
        f"about: {topic}"
    )


# =========================================================
# HANGMAN
# =========================================================

def generate_hangman_words(
    topic: str,
    use_pdf: bool,
    num_words: int,
    db: Session | None = None,
    pdf_id: int | None = None
) -> list:

    context = get_context(
        topic,
        use_pdf,
        db,
        pdf_id
    )

    prompt = f"""
You are an expert educational Hangman
game generator.

The student is currently learning:

{topic}

Use the following content as your
primary source:

{context}

Generate exactly {num_words} words
for a Hangman game.

Each word must be an important
concept or term related to:

{topic}

Return ONLY a JSON array in this format:

[
  {{
    "word": "VARIABLE",
    "hint": "A named storage location for a value"
  }}
]

RULES:

- Words must be UPPERCASE.
- Words must contain only letters.
- Words must be single words.
- No spaces.
- No hyphens.
- Words must be 4 to 12 characters.
- Words must be directly related to the topic.
- Hints must help the student without
  directly revealing the word.
- Avoid obscure or irrelevant words.
- Avoid duplicate words.
- Return ONLY the JSON array.
"""

    return call_llm(prompt)


# =========================================================
# CROSSWORD
# =========================================================

def generate_crossword_words(
    topic: str,
    use_pdf: bool,
    num_words: int,
    db: Session | None = None,
    pdf_id: int | None = None
) -> list:

    context = get_context(
        topic,
        use_pdf,
        db,
        pdf_id
    )

    prompt = f"""
You are an expert educational
crossword puzzle generator.

The student is currently learning:

{topic}

Use the following content as your
primary source:

{context}

Generate exactly {num_words} words
for a crossword puzzle.

Each word must be an important
concept or term related to:

{topic}

Return ONLY a JSON array:

[
  {{
    "word": "REACTION",
    "clue": "A process in which substances change"
  }}
]

RULES:

- Words must be UPPERCASE.
- Words must contain only letters.
- Words must be single words.
- No spaces.
- No hyphens.
- Words must be 3 to 10 characters.
- Clues must be short and clear.
- Clues must not directly contain the answer.
- Words must be related to the topic.
- Avoid duplicate words.
- Prefer words that share letters with
  other generated words.
- Return ONLY the JSON array.
"""

    return call_llm(prompt)