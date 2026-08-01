import fitz
from sentence_transformers import SentenceTransformer
import numpy as np
import json
from sqlalchemy.orm import Session
from app.models.pdf_chunk import PDFChunk

# 🔹 Load embedding model once
model = SentenceTransformer('all-MiniLM-L6-v2')

# 📄 Extract + chunk + embed PDF
def extract_text_from_pdf(file, db: Session, pdf_id: int):
    # Read PDF using PyMuPDF
    pdf_bytes = file.read()
    document = fitz.open(stream=pdf_bytes, filetype="pdf")

    text = ""

    # Extract text from every page
    for page in document:
        page_text = page.get_text("text")

        if page_text:
            text += page_text + "\n"
    document.close()

    # Clean text
    text = text.strip()
    print("Extracted text length:", len(text))
    print("Extracted text preview:", text[:500])

    if not text:
        print("WARNING: No text could be extracted from PDF")
        return 0

    # Chunking
    chunk_size = 800
    overlap = 150
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += chunk_size - overlap
    print("Number of chunks:", len(chunks))
    # Create embeddings
    embeddings = model.encode(
        chunks,
        normalize_embeddings=True
    )
    # Store chunks
    for chunk, embedding in zip(chunks, embeddings):
        db_chunk = PDFChunk(
            pdf_id=pdf_id,
            chunk_text=chunk,
            embedding=json.dumps(embedding.tolist())
        )
        db.add(db_chunk)
    db.commit()
    return len(chunks)


# 🔍 Search relevant chunks
def search_chunks(question, db: Session, pdf_id: int):
    query_embedding = model.encode(
        [question],
        normalize_embeddings=True
    )[0]
    pdf_chunks = db.query(PDFChunk).filter(
        PDFChunk.pdf_id == pdf_id
    ).all()
    if not pdf_chunks:
        return ""
    scores = []
    for chunk in pdf_chunks:
        embedding = np.array(json.loads(chunk.embedding))
        similarity = np.dot(query_embedding, embedding) / (
            np.linalg.norm(query_embedding) *
            np.linalg.norm(embedding)
        )
        scores.append((similarity, chunk.chunk_text))
    scores.sort(reverse=True)
    best_chunks = scores[:3]
    return "\n".join(
        chunk for _, chunk in best_chunks
    )