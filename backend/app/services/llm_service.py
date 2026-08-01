from groq import Groq
from app.config import GROQ_API_KEY
import re
import json

client = Groq(api_key=GROQ_API_KEY)


def generate_reply(messages: list, emotion: str) -> str:

    if emotion.lower() == "positive":
        emotion_instruction = """
The student appears interested and engaged.
- Give a detailed explanation.
- Add interesting facts when appropriate.
- Keep the tone motivating and enthusiastic.
"""

    elif emotion.lower() == "negative":
        emotion_instruction = """
The student seems confused or frustrated.
- Explain in very simple language.
- Break the concept into small steps.
- Encourage the student.
- Avoid complicated words.
"""

    elif emotion.lower() == "drowsy":
        emotion_instruction = """
The student appears tired.
- Keep the explanation concise.
- Focus only on the most important concepts.
- Use a friendly and energetic tone.
- End with a quick question to keep the student engaged.
"""

    else:
        emotion_instruction = """
The student is in a neutral state.
- Give a balanced explanation with moderate detail.
"""

    system_prompt = f"""
You are an expert AI Tutor helping school and college students.

{emotion_instruction}

Always follow these formatting rules:

1. Use clear headings.
2. Use bullet points whenever possible.
3. Highlight important keywords using **bold**.
4. Explain concepts in simple language.
5. Give examples whenever useful.
6. Use numbered steps for procedures.
7. For programming questions, include properly formatted code blocks.
8. Keep paragraphs short (2-4 lines).
9. Never return one huge paragraph.
10. End every answer with a short "Summary".

Answer naturally like a professional teacher.
"""

    try:
        conversation = [
            {
                "role": "system",
                "content": system_prompt
            }
        ]

        conversation.extend(messages)

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=conversation,
            temperature=0.4,
            max_tokens=900
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"


def clean_text(text: str) -> str:
    text = re.sub(r"\*\*", "", text)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def generate_reply_stream(messages, emotion):

    if emotion.lower() == "positive":
        emotion_instruction = """
The student appears interested and engaged.
- Give a detailed explanation.
- Add interesting facts when appropriate.
- Keep the tone motivating and enthusiastic.
"""

    elif emotion.lower() == "negative":
        emotion_instruction = """
The student seems confused or frustrated.
- Explain in very simple language.
- Break the concept into small steps.
- Encourage the student.
- Avoid complicated words.
"""

    elif emotion.lower() == "drowsy":
        emotion_instruction = """
The student appears tired.
- Keep the explanation concise.
- Focus only on the most important concepts.
- Use a friendly and energetic tone.
- End with a quick question to keep the student engaged.
"""

    else:
        emotion_instruction = """
The student is in a neutral state.
- Give a balanced explanation with moderate detail.
"""

    system_prompt = f"""
You are an expert AI Tutor helping school and college students.

{emotion_instruction}

Always follow these formatting rules:

1. Use clear headings.
2. Use bullet points whenever possible.
3. Highlight important keywords using **bold**.
4. Explain concepts in simple language.
5. Give examples whenever useful.
6. Use numbered steps for procedures.
7. For programming questions, include properly formatted code blocks.
8. Keep paragraphs short (2-4 lines).
9. Never return one huge paragraph.
10. End every answer with a short "Summary".

Answer naturally like a professional teacher.
"""

    conversation = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    conversation.extend(messages)

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=conversation,
        temperature=0.4,
        max_tokens=900,
        stream=True
    )

    for chunk in response:

        if chunk.choices:

            delta = chunk.choices[0].delta.content

            if delta:
                yield delta


def generate_notes(conversation: str) -> str:

    prompt = f"""
You are an expert teacher.

Convert the following conversation into well-structured study notes.

Rules:

- Use proper headings.
- Use bullet points.
- Highlight important terms using **bold**.
- Explain concepts simply.
- Include examples if discussed.
- Remove greetings and unnecessary conversation.
- End with a short Summary.

Conversation:

{conversation}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert note maker."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1200
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"Error: {str(e)}"
    


def generate_flashcards(conversation: str):

    prompt = f"""
You are an expert teacher.

Read the conversation and generate study flashcards.

Rules:

- Create between 10 and 20 flashcards.
- Focus only on important concepts.
- Keep answers short (1-3 sentences).
- Don't include greetings.
- Don't repeat questions.

Return ONLY valid JSON.

Example:

[
    {{
        "question":"What is DBMS?",
        "answer":"Database Management System."
    }},
    {{
        "question":"What is Normalization?",
        "answer":"It reduces redundancy."
    }}
]

Conversation:

{conversation}
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "Return only JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_tokens=1500
        )

        return json.loads(response.choices[0].message.content)

    except Exception as e:

        return [
            {
                "question": "Error",
                "answer": str(e)
            }
        ]