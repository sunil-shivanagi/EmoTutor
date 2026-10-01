# EmoTutor 🧠📚

> **An emotion-aware AI tutoring platform that adapts learning support to the student's current state.**

EmoTutor is a full-stack AI learning application built with a Python/FastAPI backend and a browser-based HTML/CSS/JavaScript frontend. It combines conversational AI, facial-state detection, PDF-based semantic retrieval, learning-topic tracking, quizzes, educational games, study sessions, notes, and text-to-speech.

## ✨ Features

- 🤖 AI conversational tutor powered through the Groq API.
- 😊 Facial-state detection using a trained ResNet18 model, PyTorch/TorchVision, MediaPipe Face Mesh and OpenCV.
- 😴 Separate drowsiness detection using Eye Aspect Ratio (EAR) from MediaPipe landmarks.
- 🧑‍🏫 Adaptive explanations based on Positive, Negative, Drowsy and Neutral states.
- 📄 PDF upload and document-grounded learning.
- 🔎 Semantic PDF retrieval using Sentence Transformers (`all-MiniLM-L6-v2`) and database-stored embeddings.
- 🧠 LLM-based learning-topic analysis: `none`, `continue`, `new`, or `existing`.
- 🧪 AI-generated quizzes.
- 🎮 Educational Hangman and Crossword generation.
- 📝 AI-generated study notes.
- 💬 Persistent chat and learning sessions.
- 🔊 ElevenLabs backend TTS plus browser SpeechSynthesis support.
- 🔐 JWT authentication and bcrypt password hashing.
- 🗄️ PostgreSQL database through SQLAlchemy ORM.
- 🐳 Dockerized backend.

## 🏗️ System Architecture

```text
                         ┌──────────────────────────┐
                         │         STUDENT          │
                         │ Chat • Camera • PDF     │
                         │ Quiz • Games • Notes    │
                         │ TTS • Study Sessions   │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                    ┌─────────────────────────────────┐
                    │           FRONTEND              │
                    │ HTML + CSS + Vanilla JavaScript │
                    │ Fetch • Camera • Speech • UI   │
                    └───────────────┬─────────────────┘
                                    │ HTTP / REST
                                    ▼
                    ┌─────────────────────────────────┐
                    │         FASTAPI BACKEND         │
                    │                                 │
                    │ Auth │ Chat │ Emotion │ PDF     │
                    │ Quiz │ Game │ Notes │ Sessions  │
                    │ Study │ TTS                     │
                    └───────┬──────────┬──────────────┘
                            │          │
              ┌─────────────┘          └─────────────────┐
              ▼                                          ▼
     ┌──────────────────┐                      ┌─────────────────────┐
     │    PostgreSQL    │                      │    AI / ML Layer   │
     │                  │                      │                     │
     │ SQLAlchemy ORM   │                      │ Groq LLM            │
     │ Users            │                      │ ResNet18            │
     │ Chats/Sessions   │                      │ PyTorch/TorchVision │
     │ PDFs/Chunks      │                      │ MediaPipe/OpenCV    │
     │ Learning Topics  │                      │ SentenceTransformers│
     └──────────────────┘                      └──────────┬──────────┘
                                                         │
                           ┌─────────────────────────────┘
                           ▼
                 ┌─────────────────────────┐
                 │   PDF / RAG PIPELINE    │
                 │                         │
                 │ PyMuPDF → Cleaning      │
                 │ → Chunking → Embeddings │
                 │ → Similarity Search      │
                 │ → LLM Context           │
                 └─────────────────────────┘
```

## 🔄 AI Tutor Flow

```text
Student question
      ↓
Frontend sends message + session + current detected state
      ↓
FastAPI chat route
      ↓
Load user/session/history
      ↓
Analyze learning topic
      ↓
If PDF is attached → retrieve relevant document chunks
      ↓
Build emotion-aware tutor prompt
      ↓
Groq LLM: openai/gpt-oss-120b
      ↓
Tutor response
      ↓
Save chat/session/topic information
      ↓
Return response to frontend
```

## 🧠 Emotion & Drowsiness Pipeline

```text
Camera frame
   ↓
OpenCV image decoding
   ↓
MediaPipe Face Mesh
   ↓
Face landmarks
   ├── No face → No Face
   │
   └── Eye landmarks → EAR calculation
                      ├── EAR below threshold → Drowsy
                      │
                      └── Otherwise
                           ↓
                       Grayscale face
                           ↓
                    Resize 224 × 224
                           ↓
                       ResNet18
                           ↓
                    2-class classifier
                      ├── Positive
                      └── Negative
```

The current `config.json` maps `happy` and `neutral` to **Positive**, and `sad` and `disgust` to **Negative**. Drowsiness is handled separately by EAR and is not a third ResNet class. The model is a ResNet18 with a 2-output head stored as `backend/app/models/final_emotion.pth`. fileciteturn7file0L2-L6 fileciteturn8file0L2-L6

## 🧑‍🏫 Adaptive Teaching

The detected state changes the LLM system instructions:

| State | Teaching style |
|---|---|
| **Positive** | Encouraging, engaging and reasonably detailed |
| **Negative** | Simple language, smaller steps and supportive guidance |
| **Drowsy** | Concise, high-priority information and short sections |
| **Neutral** | Balanced explanations with useful examples |

This behavior is implemented in the LLM service. fileciteturn10file0L2-L3

## 🤖 Generative AI Layer

The Groq API and `openai/gpt-oss-120b` are used for multiple tasks:

- AI tutoring
- Learning-topic classification
- Quiz generation
- Educational game generation
- Study-note generation

The topic service uses conversation history, current topic, previous topics and PDF context to classify messages as `none`, `continue`, `new` or `existing`. fileciteturn25file0L2-L3

The LLM service also supports streaming responses. fileciteturn13file1L20-L32

## 📄 PDF / RAG-Style Pipeline

The repository implements a RAG-style document pipeline:

```text
PDF
 ↓
PyMuPDF (fitz)
 ↓
Page-by-page text extraction
 ↓
Text cleaning
 ↓
Document-aware chunking
 ├─ target ≈ 1400 characters
 ├─ minimum ≈ 300 characters
 └─ overlap ≈ 250 characters
 ↓
SentenceTransformer: all-MiniLM-L6-v2
 ↓
Normalized embeddings
 ↓
Stored in PostgreSQL PDFChunk records
 ↓
User question → query embedding
 ↓
Dot-product similarity
 ↓
Top-K relevant chunks
 ↓
Context supplied to LLM
 ↓
Grounded tutor / quiz / game response
```

The important architecture detail is that the current implementation calculates similarity directly against embeddings stored in the database using NumPy. **FAISS is present in `requirements.txt`, but it is not currently the active retrieval engine.** fileciteturn20file0L2-L7

## 🎮 Educational Games

The game service can use PDF context and the LLM to generate:

- **Hangman**
- **Crossword**

The generated game data is requested as structured JSON for frontend rendering. fileciteturn21file0L2-L7

## 🔊 Text-to-Speech

Two speech approaches exist:

- **ElevenLabs API** in the backend using `eleven_multilingual_v2` and `ELEVENLABS_API_KEY`.
- **Browser SpeechSynthesis API** in the frontend.

The backend TTS service calls the ElevenLabs API and returns generated audio bytes. fileciteturn24file0L2-L6

## 🔐 Authentication & Database

Authentication uses JWT-based authorization and bcrypt password hashing through Passlib. fileciteturn22file13L229-L236

PostgreSQL is accessed through SQLAlchemy ORM. fileciteturn15file0L2-L6

Main persisted concepts include:

```text
User
 └── Chat Sessions
      ├── Chat Messages
      ├── Learning Topics
      ├── Study Sessions
      └── Uploaded PDFs
             └── PDF Chunks + Embeddings
```

## 🛠️ Technology Stack

### Frontend

- **HTML5** — UI structure
- **CSS3** — styling
- **Vanilla JavaScript** — application logic
- **Fetch API** — REST communication
- **MediaDevices API** — camera access
- **SpeechSynthesis API** — browser TTS
- **LocalStorage** — client-side token/session state

The frontend uses `navigator.mediaDevices.getUserMedia(...)` for camera access. fileciteturn13file2L36-L45

### Backend

- **Python 3.11**
- **FastAPI** — REST API
- **Uvicorn** — ASGI server
- **Pydantic** — validation/schemas
- **SQLAlchemy** — ORM
- **PostgreSQL** — relational database
- **JWT** — authentication
- **Passlib + bcrypt** — password hashing
- **python-dotenv** — environment configuration

FastAPI registers routes for auth, chat, PDF, quiz, emotion, session, game, notes and study functionality. fileciteturn6file0L2-L6

### AI / ML

- **PyTorch** — ML inference
- **TorchVision** — ResNet18 and image transforms
- **ResNet18** — facial-state classifier
- **MediaPipe Face Mesh** — face/eye landmarks
- **OpenCV** — frame/image processing
- **NumPy** — numerical calculations and similarity
- **Sentence Transformers** — semantic embeddings
- **all-MiniLM-L6-v2** — embedding model
- **Groq API** — LLM inference
- **openai/gpt-oss-120b** — configured generative model

### Document / Retrieval

- **PyMuPDF (`fitz`)** — PDF extraction
- **Sentence Transformers** — embeddings
- **PostgreSQL** — chunk/embedding persistence
- **NumPy dot product** — similarity calculation

### Speech

- **ElevenLabs API** — server-side TTS
- **Web Speech API** — browser TTS

### Deployment

- **Docker** — backend containerization
- **Python 3.11-slim** — container base image

The Dockerfile installs Linux libraries needed by OpenCV/MediaPipe, installs Python dependencies, exposes port 8000 and starts Uvicorn. fileciteturn9file0L2-L6

## 📁 Repository Structure

```text
EmoTutor/
├── backend/
│   ├── app/
│   │   ├── auth/
│   │   │   ├── dependencies.py
│   │   │   ├── jwt_handler.py
│   │   │   └── security.py
│   │   ├── models/
│   │   │   ├── chat.py
│   │   │   ├── chat_message.py
│   │   │   ├── chat_session.py
│   │   │   ├── config.json
│   │   │   ├── emotion_model.py
│   │   │   ├── final_emotion.pth
│   │   │   ├── learning_topic.py
│   │   │   ├── pdf.py
│   │   │   ├── pdf_chunk.py
│   │   │   ├── schemas.py
│   │   │   ├── uploaded_pdf.py
│   │   │   └── user.py
│   │   ├── routes/
│   │   │   ├── auth.py
│   │   │   ├── chat.py
│   │   │   ├── emotion.py
│   │   │   ├── game.py
│   │   │   ├── notes.py
│   │   │   ├── pdf.py
│   │   │   ├── quiz.py
│   │   │   ├── session.py
│   │   │   ├── study_routes.py
│   │   │   └── tts.py
│   │   ├── services/
│   │   │   ├── emotion_service.py
│   │   │   ├── game_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── pdf_service.py
│   │   │   ├── quiz_service.py
│   │   │   ├── topic_service.py
│   │   │   ├── tutor_service.py
│   │   │   ├── tts_service.py
│   │   │   └── vector_db.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── Dockerfile
│   ├── .dockerignore
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── script.js
│   └── styles.css
└── .gitignore
```

The repository contains a roughly **44.8 MB** trained model file `final_emotion.pth`. fileciteturn17file0L2-L2

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- Git
- Groq API key
- ElevenLabs API key if using backend TTS
- Modern browser with camera permission for emotion detection

### 1. Clone

```bash
git clone https://github.com/sunil-shivanagi/EmoTutor.git
cd EmoTutor
```

### 2. Create virtual environment

```bash
cd backend
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment variables

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
ELEVENLABS_API_KEY=your_elevenlabs_api_key
DATABASE_URL=postgresql://username:password@localhost:5432/emotutor
SECRET_KEY=your_secret_key
ALGORITHM=HS256
```

Never commit API keys, passwords or `.env` files.

### 5. PostgreSQL

Create a PostgreSQL database named `emotutor`, or update `DATABASE_URL` to your database.

### 6. Start backend

From `backend/`:

```bash
uvicorn app.main:app --reload
```

API: `http://127.0.0.1:8000`

Swagger/OpenAPI: `http://127.0.0.1:8000/docs`

### 7. Start frontend

From `frontend/`:

```bash
python -m http.server 5500
```

Open `http://127.0.0.1:5500` and ensure the frontend API URL points to the backend.

## 🐳 Docker

```bash
cd backend
docker build -t emotutor-backend .
docker run -p 8000:8000 --env-file .env emotutor-backend
```

PostgreSQL still needs to be reachable using `DATABASE_URL`.

## 🔑 Environment Variables

| Variable | Purpose |
|---|---|
| `GROQ_API_KEY` | LLM/AI features |
| `ELEVENLABS_API_KEY` | Backend text-to-speech |
| `DATABASE_URL` | PostgreSQL connection |
| `SECRET_KEY` | JWT security |
| `ALGORITHM` | JWT algorithm configuration |

## ⚠️ Important Implementation Notes

### Emotion model

Do **not** describe the current system as a single 3-class/4-class emotion model. It currently uses a **2-class ResNet18 classifier** plus a separate EAR-based drowsiness detector. fileciteturn7file0L2-L6

### Retrieval

Do **not** claim FAISS is currently the active vector database. `faiss-cpu` exists in the dependency list, but the inspected retrieval implementation performs similarity directly over stored embeddings using NumPy. fileciteturn20file0L2-L7

### LangChain / LangGraph

`langchain` and `langgraph` are present in `requirements.txt`, but the inspected main AI services make direct Groq API calls. Treat LangChain/LangGraph as installed dependencies rather than core architecture unless the active code is changed to use them. fileciteturn5file0L2-L6

### Production CORS

The current FastAPI application allows all origins. For production, restrict CORS to the actual frontend origin. fileciteturn11file0L2-L8

## 🔒 Recommended Production Improvements

- Restrict CORS.
- Add rate limiting for LLM and upload endpoints.
- Validate uploaded PDF size/type.
- Add database migrations.
- Add unit and integration tests.
- Add structured logging and monitoring.
- Protect model/API resources against abuse.
- Consider Git LFS/model storage for the large `.pth` artifact.
- Add Docker Compose for frontend + backend + PostgreSQL.
- Add GitHub Actions CI/CD.
- Add ML evaluation metrics: accuracy, precision, recall, F1 and confusion matrix.
- Add temporal smoothing/confidence scoring for emotion detection.
- Add source/page citations to PDF-grounded answers.

## 🔮 Future Improvements

- More emotion classes and a better-trained emotion model.
- More robust temporal drowsiness detection.
- Dedicated vector database/FAISS if retrieval scale requires it.
- Better document citation and provenance.
- Automated testing and CI/CD.
- Production deployment configuration.
- Monitoring and analytics for learning outcomes.

## 👨‍💻 Author

**Sunil Shivanagi**

GitHub: https://github.com/sunil-shivanagi

## 📄 License

No license is currently specified in the repository. Add an appropriate open-source license if you plan to distribute the project publicly.
