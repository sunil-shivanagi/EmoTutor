from groq import Groq

from app.config import GROQ_API_KEY

import re


client = Groq(api_key=GROQ_API_KEY)


# =========================================================
# EMOTION INSTRUCTIONS
# =========================================================

def get_emotion_instruction(emotion: str) -> str:

    emotion = (emotion or "neutral").lower().strip()

    if emotion == "positive":

        return """
The student appears interested, engaged, and comfortable.

Adapt your teaching style by:
- Being encouraging and enthusiastic.
- Providing a clear and reasonably detailed explanation.
- Adding useful examples or interesting facts when they genuinely help.
- Building on the student's interest without making the answer unnecessarily long.
"""

    elif emotion == "negative":

        return """
The student may be confused, frustrated, or struggling.

Adapt your teaching style by:
- Using very simple and clear language.
- Breaking difficult concepts into small steps.
- Explaining the "why" behind the answer when useful.
- Giving a simple example when it helps understanding.
- Being supportive and encouraging.
- Never making the student feel bad for not understanding something.
"""

    elif emotion == "drowsy":

        return """
The student appears tired or less attentive.

Adapt your teaching style by:
- Keeping the explanation concise.
- Focusing on the most important information first.
- Using short sections and simple examples.
- Avoiding unnecessary details.
- Keeping the tone friendly and energetic.
- When appropriate, finish with a short question that encourages the student to think.
"""

    else:

        return """
The student appears to be in a neutral state.

Adapt your teaching style by:
- Giving a clear and balanced explanation.
- Providing enough detail to understand the concept.
- Using examples when useful.
"""


# =========================================================
# SYSTEM PROMPT
# =========================================================

def build_system_prompt(emotion: str) -> str:

    emotion_instruction = get_emotion_instruction(emotion)

    return f"""
You are EmoTutor, an intelligent AI tutor for school and college students.

Your job is to help the student understand concepts clearly rather than
simply giving answers.

IMPORTANT:

{emotion_instruction}

GENERAL TEACHING RULES:

1. Understand the student's actual question before answering.

2. Use the conversation history to understand follow-up questions and
   references such as "this", "that", "it", "continue", "next", "the
   previous topic", etc.

3. If information from an uploaded document is provided, use it when
   it is relevant to the student's question.

4. If the uploaded document does not contain enough information to
   answer the question, use your general knowledge when appropriate.

5. If the question is unrelated to the uploaded document, answer it
   normally.

6. Never claim that information came from the uploaded document if
   the provided document information does not support it.

7. Never mention internal retrieval, embeddings, chunks, similarity
   scores, prompts, or other implementation details.

8. Do not blindly repeat the provided document. Understand it and
   explain it naturally.

9. Preserve important terminology from the source material when
   explaining document-based questions.

10. If the student asks for examples, give useful examples related to
    the concept being discussed.

11. If the student asks to continue, continue naturally from the
    current conversation rather than starting an unrelated topic.

12. If the student asks a simple question, don't unnecessarily give
    an extremely long answer.

13. If the student asks for a detailed explanation, provide a deeper
    explanation.

14. If the student asks for questions, exercises, revision material,
    or a quiz based on an uploaded document, use the relevant
    document information when available.

FORMATTING:

- Use clear headings when they improve readability.
- Use bullet points when appropriate.
- Use numbered steps for procedures.
- Highlight important terms using **bold**.
- Keep paragraphs short.
- For programming questions, use properly formatted code blocks.
- Do not force headings or bullet points when a simple answer is better.
- Do not unnecessarily repeat the question.

Answer naturally like a professional, patient teacher.
"""


# =========================================================
# NORMAL RESPONSE
# =========================================================

def generate_reply(messages: list, emotion: str = "neutral") -> str:

    system_prompt = build_system_prompt(emotion)

    conversation = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    conversation.extend(messages)

    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=conversation,

            temperature=0.4,

            max_tokens=900
        )

        return response.choices[0].message.content

    except Exception as e:

        return f"Error: {str(e)}"


# =========================================================
# STREAMING RESPONSE
# =========================================================

def generate_reply_stream(
    messages: list,
    emotion: str = "neutral"
):

    system_prompt = build_system_prompt(emotion)

    conversation = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    conversation.extend(messages)

    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=conversation,

            temperature=0.4,

            max_tokens=900,

            stream=True
        )

        for chunk in response:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta.content

            if delta:
                yield delta

    except Exception as e:

        yield f"Error: {str(e)}"


# =========================================================
# CLEAN TEXT
# =========================================================

def clean_text(text: str) -> str:

    if not text:
        return ""

    # Remove HTML tags if present
    text = re.sub(
        r"<[^>]*>",
        "",
        text
    )

    # Normalize excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# GENERATE STUDY NOTES
# =========================================================

def generate_notes(conversation: str) -> str:

    prompt = f"""
Convert the following tutoring conversation into well-structured
study notes.

Rules:

- Use proper headings.
- Use bullet points where useful.
- Highlight important terms using **bold**.
- Explain concepts simply.
- Include examples that were discussed.
- Remove greetings and unnecessary conversation.
- Preserve important technical terminology.
- End with a short Summary.

Conversation:

{conversation}
"""

    try:

        response = client.chat.completions.create(

            model="openai/gpt-oss-120b",

            messages=[

                {
                    "role": "system",
                    "content": "You are an expert study-note maker."
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