from app.services.pdf_service import search_chunks
from app.config import GROQ_API_KEY
from groq import Groq
import json, re

client = Groq(api_key=GROQ_API_KEY)

def call_llm(prompt: str) -> list:
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "You are a word game generator. Return only valid JSON arrays."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"```json|```", "", raw).strip()
        return json.loads(raw)
    except Exception as e:
        print("Game generation error:", e)
        return []

def get_context(topic: str, use_pdf: bool) -> str:
    if use_pdf:
        context = search_chunks(topic)
        if context and len(context.strip()) > 50:
            return context
    return f"General knowledge about: {topic}"

def generate_hangman_words(topic: str, use_pdf: bool, num_words: int) -> list:
    context = get_context(topic, use_pdf)

    prompt = f"""
You are a word game generator for students.

Context: {context}
Topic: {topic}

Generate exactly {num_words} words for a Hangman game.
Each word must be a key term related to the topic.
Return ONLY a JSON array like this:
[
  {{"word": "PYTHON", "hint": "A popular programming language named after a snake"}},
  {{"word": "VARIABLE", "hint": "A container that stores data values in programming"}}
]

Rules:
- Words must be UPPERCASE
- Words must be single words only (no spaces)
- Words must be between 4 and 12 characters
- Hints must be clear definitions a student can understand
- Return ONLY the JSON array, no extra text
"""
    return call_llm(prompt)


def generate_crossword_words(topic: str, use_pdf: bool, num_words: int) -> list:
    context = get_context(topic, use_pdf)

    prompt = f"""
You are a crossword puzzle generator for students.

Context: {context}
Topic: {topic}

Generate exactly {num_words} words for a crossword puzzle.
Return ONLY a JSON array like this:
[
  {{"word": "PYTHON", "clue": "Popular programming language named after a snake"}},
  {{"word": "LOOP", "clue": "A programming construct that repeats code"}},
  {{"word": "DATA", "clue": "Information stored and processed by a computer"}}
]

Rules:
- Words must be UPPERCASE single words only
- Words must be between 3 and 10 characters
- Clues must be short and clear (under 60 characters)
- Words should be able to intersect (share common letters)
- Return ONLY the JSON array, no extra text
"""
    return call_llm(prompt)