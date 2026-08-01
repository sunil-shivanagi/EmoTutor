from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
import uuid

from app.services.pdf_service import extract_text_from_pdf, search_chunks
from app.services.llm_service import generate_reply, clean_text
from app.services.tutor_service import start_study_session

from sqlalchemy.orm import Session
from fastapi import Depends

from app.database import get_db
from app.models.user import User
from app.models.pdf import PDF
from app.auth.dependencies import get_current_user

import os
import shutil

router = APIRouter()

# 📤 Upload PDF
@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    os.makedirs("uploads", exist_ok=True)

    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join("uploads", filename)

    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    pdf = PDF(
        user_id=current_user.id,
        filename=file.filename,
        filepath=filepath
    )

    db.add(pdf)
    db.commit()
    db.refresh(pdf)

    with open(filepath, "rb") as pdf_file:
        num_chunks = extract_text_from_pdf(
            pdf_file,
            db,
            pdf.id
    )
    print("Uploaded PDF ID:", pdf.id)
    print("Chunks created:", num_chunks)

    return {
        "message": "PDF uploaded successfully",
        "pdf_id": pdf.id,
        "chunks_created": num_chunks
    }


# ❓ Request model
class QueryRequest(BaseModel):
    pdf_id: int
    question: str


# ❓ Ask question from PDF
@router.post("/ask-pdf")
def ask_pdf(
    request: QueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdf = db.query(PDF).filter(
        PDF.id == request.pdf_id,
        PDF.user_id == current_user.id
    ).first()

    if pdf is None:
        return {
            "message": "PDF not found."
        }
    print("=" * 50)
    print("PDF ID:", request.pdf_id)
    print("Question:", request.question)
    context = search_chunks(
        request.question,
        db,
        request.pdf_id
    )
    print("\nRetrieved Context:\n")
    print(context)
    print("=" * 50)

    # ✅ CASE 1: answer found in uploaded PDF
    if context and len(context.strip()) > 50:

        prompt = f"""
You are an AI tutor answering ONLY from the uploaded PDF.

Rules:

1. Read the CONTEXT carefully.
2. Answer ONLY using the information present in the CONTEXT.
3. If the answer is not present in the CONTEXT, reply exactly:

"I couldn't find this information in the uploaded PDF."

4. Do NOT use your own knowledge.
5. If the question asks about the whole PDF, summarize the PDF.

--------------------
CONTEXT

{context}

--------------------

QUESTION

{request.question}
"""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        answer = generate_reply(messages, "neutral")
        answer = clean_text(answer)

        # create reading session
        session_id = str(uuid.uuid4())
        reading_time = start_study_session(session_id, answer)

        return {
            "answer": answer,
            "source": "pdf",
            "session_id": session_id,
            "reading_time": reading_time
        }

    # ✅ CASE 2: fallback to AI explanation
    else:

        prompt = f"""
You are a helpful AI tutor.

Answer the following question clearly with examples
so that a beginner can understand.

Question:
{request.question}
"""

        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]

        answer = generate_reply(messages, "neutral")
        answer = clean_text(answer)

        # create reading session
        session_id = str(uuid.uuid4())
        reading_time = start_study_session(session_id, answer)

        return {
            "answer": answer,
            "source": "ai",
            "session_id": session_id,
            "reading_time": reading_time
        }

# 📂 Get all PDFs uploaded by current user
@router.get("/my-pdfs")
def get_my_pdfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdfs = db.query(PDF).filter(
        PDF.user_id == current_user.id
    ).order_by(PDF.uploaded_at.desc()).all()

    return [
        {
            "id": pdf.id,
            "filename": pdf.filename,
            "uploaded_at": pdf.uploaded_at
        }
        for pdf in pdfs
    ]

@router.delete("/delete-pdf/{pdf_id}")
def delete_pdf(
    pdf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdf = db.query(PDF).filter(
        PDF.id == pdf_id,
        PDF.user_id == current_user.id
    ).first()

    if pdf is None:
        return {
            "message": "PDF not found."
        }

    if os.path.exists(pdf.filepath):
        os.remove(pdf.filepath)

    db.delete(pdf)
    db.commit()

    return {
        "message": "PDF deleted successfully."
    }


@router.get("/pdfs")
def get_user_pdfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdfs = (
        db.query(PDF)
        .filter(PDF.user_id == current_user.id)
        .order_by(PDF.uploaded_at.desc())
        .all()
    )

    return [
        {
            "id": pdf.id,
            "filename": pdf.filename,
            "uploaded_at": pdf.uploaded_at
        }
        for pdf in pdfs
    ]