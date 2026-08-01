from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine

# Import models
from app.models.user import User
from app.models.chat import Chat
from app.models.pdf import PDF
from app.models.pdf_chunk import PDFChunk
from app.models.chat_session import ChatSession
from app.routes import notes
from app.routes import flashcards

from app.routes.study_routes import router as study_router
# Import routes
from app.routes import (
    auth,
    chat,
    pdf,
    quiz,
    emotion,
    session,
    game,
    # tts,
)



app = FastAPI(title="EmoTutor API")

# Create database tables
Base.metadata.create_all(bind=engine)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Later we'll change this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(pdf.router)
app.include_router(quiz.router)
app.include_router(emotion.router)
app.include_router(session.router)
app.include_router(game.router)
# app.include_router(tts.router)
app.include_router(notes.router)
app.include_router(flashcards.router)
app.include_router(study_router)

@app.get("/")
def home():
    return {"message": "EmoTutor Backend Running 🚀"}