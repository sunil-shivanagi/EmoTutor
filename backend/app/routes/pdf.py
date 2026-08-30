from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

import uuid
import os
import shutil

from app.services.pdf_service import extract_text_from_pdf

from app.database import get_db
from app.models.user import User
from app.models.pdf import PDF
from app.auth.dependencies import get_current_user


router = APIRouter()


# =========================================================
# UPLOAD PDF
# =========================================================

@router.post("/upload-pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    # -----------------------------------------------------
    # Validate file
    # -----------------------------------------------------

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file selected."
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # -----------------------------------------------------
    # Create uploads directory
    # -----------------------------------------------------

    os.makedirs(
        "uploads",
        exist_ok=True
    )

    # -----------------------------------------------------
    # Create unique filename
    # -----------------------------------------------------

    filename = (
        f"{uuid.uuid4()}_{file.filename}"
    )

    filepath = os.path.join(
        "uploads",
        filename
    )

    # -----------------------------------------------------
    # Save PDF
    # -----------------------------------------------------

    try:

        with open(filepath, "wb") as buffer:

            shutil.copyfileobj(
                file.file,
                buffer
            )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=f"Could not save PDF: {str(e)}"
        )

    # -----------------------------------------------------
    # Create PDF database record
    # -----------------------------------------------------

    pdf = PDF(
        user_id=current_user.id,
        filename=file.filename,
        filepath=filepath
    )

    db.add(pdf)
    db.commit()
    db.refresh(pdf)

    # -----------------------------------------------------
    # Extract + chunk + embed
    # -----------------------------------------------------

    try:

        with open(
            filepath,
            "rb"
        ) as pdf_file:

            num_chunks = extract_text_from_pdf(
                pdf_file,
                db,
                pdf.id
            )

    except Exception as e:

        # Remove database record if processing failed
        db.delete(pdf)
        db.commit()

        # Remove saved file
        if os.path.exists(filepath):
            os.remove(filepath)

        raise HTTPException(
            status_code=500,
            detail=f"Could not process PDF: {str(e)}"
        )

    # -----------------------------------------------------
    # Make sure PDF actually contained usable text
    # -----------------------------------------------------

    if num_chunks == 0:

        db.delete(pdf)
        db.commit()

        if os.path.exists(filepath):
            os.remove(filepath)

        raise HTTPException(
            status_code=400,
            detail=(
                "Could not extract usable text "
                "from this PDF."
            )
        )

    print(
        "Uploaded PDF ID:",
        pdf.id
    )

    print(
        "Chunks created:",
        num_chunks
    )

    # -----------------------------------------------------
    # Response
    # -----------------------------------------------------

    return {
        "message": "PDF uploaded successfully",
        "pdf_id": pdf.id,
        "filename": pdf.filename,
        "chunks_created": num_chunks
    }


# =========================================================
# GET USER PDFs
# =========================================================

@router.get("/my-pdfs")
def get_my_pdfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdfs = (
        db.query(PDF)
        .filter(
            PDF.user_id == current_user.id
        )
        .order_by(
            PDF.uploaded_at.desc()
        )
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


# =========================================================
# GET USER PDFs
# =========================================================

@router.get("/pdfs")
def get_user_pdfs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdfs = (
        db.query(PDF)
        .filter(
            PDF.user_id == current_user.id
        )
        .order_by(
            PDF.uploaded_at.desc()
        )
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


# =========================================================
# DELETE PDF
# =========================================================

@router.delete("/delete-pdf/{pdf_id}")
def delete_pdf(
    pdf_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    pdf = (
        db.query(PDF)
        .filter(
            PDF.id == pdf_id,
            PDF.user_id == current_user.id
        )
        .first()
    )

    if pdf is None:

        raise HTTPException(
            status_code=404,
            detail="PDF not found."
        )

    # -----------------------------------------------------
    # Delete physical file
    # -----------------------------------------------------

    if os.path.exists(pdf.filepath):
        os.remove(pdf.filepath)

    # -----------------------------------------------------
    # Delete database record
    #
    # PDFChunk uses ON DELETE CASCADE, so its chunks
    # will also be deleted.
    # -----------------------------------------------------

    db.delete(pdf)
    db.commit()

    return {
        "message": "PDF deleted successfully."
    }