from fastapi import APIRouter
from pydantic import BaseModel
from app.services.quiz_service import generate_quiz

router = APIRouter()

class QuizRequest(BaseModel):
    topic: str
    quiz_type: str   # "mcq", "truefalse", "shortanswer"
    num_questions: int = 5
    use_pdf: bool = True   # 👈 new field

@router.post("/generate-quiz")
def generate_quiz_route(request: QuizRequest):
    quiz = generate_quiz(request.topic, request.quiz_type, request.num_questions, request.use_pdf)
    return {"quiz": quiz}