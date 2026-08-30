import time
from collections import Counter

# store temporary student sessions
student_sessions = {}


def estimate_reading_time(text):
    """
    Estimate how long a student needs to read the answer.
    Uses approximately 180 words/minute.
    Minimum: 10 seconds
    Maximum: 30 seconds
    """
    words = len(text.split())

    seconds = int((words / 180) * 60)

    return min(max(seconds, 10), 30)


def start_study_session(session_id, answer_text):
    """
    Create a new tracking session after AI gives answer
    """
    reading_time = estimate_reading_time(answer_text)

    student_sessions[session_id] = {
        "answer": answer_text,
        "start_time": time.time(),
        "reading_time": reading_time,
        "emotion_log": []
    }

    return reading_time


def update_emotion(session_id, emotion):
    """
    Store each detected emotion while student reads
    """
    if session_id in student_sessions:
        student_sessions[session_id]["emotion_log"].append(emotion)


def analyze_session(session_id):
    """
    Decide what tutor should do after reading
    """
    if session_id not in student_sessions:
        return {
            "status": "No Session"
        }

    emotions = student_sessions[session_id]["emotion_log"]

    if not emotions:
        return {
            "status": "No Data"
        }

    counts = Counter(emotions)

    positive = counts.get("Positive", 0)
    negative = counts.get("Negative", 0)
    drowsy = counts.get("Drowsy", 0)
    noface = counts.get("No Face", 0)

    if drowsy >= 3:
        action = "break"
        message = "You seem tired. Would you like to take a short break?"

    elif negative > positive:
        action = "simplify"
        message = "You seem unsure. Would you like a simpler explanation?"

    elif positive >= negative:
        action = "quiz"
        message = "You seem comfortable. Would you like a quick quiz?"

    elif noface >= 3:
        action = "refocus"
        message = "You seem distracted. Shall we continue?"

    else:
        action = "check"
        message = "Would you like more help?"

    return {
        "status": "Completed",
        "emotion_counts": dict(counts),
        "action": action,
        "message": message
    }