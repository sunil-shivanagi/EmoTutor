from fastapi import APIRouter
from pydantic import BaseModel
from app.services.game_service import generate_hangman_words, generate_crossword_words

router = APIRouter()

class GameRequest(BaseModel):
    topic: str
    use_pdf: bool = False
    num_words: int = 5

@router.post("/generate-hangman")
def hangman(request: GameRequest):
    words = generate_hangman_words(request.topic, request.use_pdf, request.num_words)
    return {"words": words}

@router.post("/generate-crossword")
def crossword(request: GameRequest):
    words = generate_crossword_words(request.topic, request.use_pdf, request.num_words)
    return {"words": words}