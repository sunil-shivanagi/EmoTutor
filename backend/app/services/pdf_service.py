import fitz
import json
import re
from typing import List, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.pdf_chunk import PDFChunk


# =========================================================
# LOAD EMBEDDING MODEL ONCE
# =========================================================

model = SentenceTransformer("all-MiniLM-L6-v2")


# =========================================================
# CONFIGURATION
# =========================================================

# Target chunk size in characters.
# We don't split strictly at this number.
TARGET_CHUNK_SIZE = 1400

# Minimum useful chunk size.
MIN_CHUNK_SIZE = 300

# Number of characters carried into the next chunk.
OVERLAP = 250

# Number of candidate chunks returned to the LLM.
TOP_K = 4


# =========================================================
# TEXT CLEANING
# =========================================================

def clean_pdf_text(text: str) -> str:
    """
    Clean common PDF extraction problems without destroying
    the actual document content.
    """

    if not text:
        return ""

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Join words broken by a hyphen at a line ending.
    # Example:
    # photo-
    # synthesis
    # ->
    # photosynthesis
    text = re.sub(
        r"(\w)-\s*\n\s*(\w)",
        r"\1\2",
        text
    )

    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Remove excessive spaces
    text = re.sub(
        r"[ ]{2,}",
        " ",
        text
    )

    # Reduce excessive blank lines
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )

    return text.strip()


# =========================================================
# PAGE / DOCUMENT STRUCTURE
# =========================================================

def extract_pdf_pages(file) -> List[Dict[str, Any]]:
    """
    Extract text page-by-page.

    Keeping pages separate is important because later retrieval
    needs to know where information came from.
    """

    pdf_bytes = file.read()

    document = fitz.open(
        stream=pdf_bytes,
        filetype="pdf"
    )

    pages = []

    for page_number, page in enumerate(document, start=1):

        raw_text = page.get_text("text")

        cleaned_text = clean_pdf_text(
            raw_text
        )

        if not cleaned_text:
            continue

        pages.append({
            "page_number": page_number,
            "text": cleaned_text
        })

    document.close()

    return pages


# =========================================================
# HEADING DETECTION
# =========================================================

def looks_like_heading(line: str) -> bool:
    """
    Generic heading detection.

    This does NOT look for words such as 'chapter' or
    'section'. It uses document formatting characteristics
    instead.
    """

    line = line.strip()

    if not line:
        return False

    if len(line) > 120:
        return False

    # Avoid treating normal long sentences as headings.
    words = line.split()

    if len(words) > 15:
        return False

    # Numbered headings are common in textbooks/documents.
    if re.match(
        r"^\d+(\.\d+)*[\s.)-]+",
        line
    ):
        return True

    # Short lines ending without sentence punctuation
    if len(words) <= 10 and not re.search(
        r"[.!?,;:]$",
        line
    ):
        return True

    return False


# =========================================================
# CHUNK CREATION
# =========================================================

def create_chunks(
    pages: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Create document-aware chunks.

    Chunks retain:
    - page number
    - heading when detectable
    - order within document

    We prefer paragraph boundaries instead of blindly slicing
    every N characters.
    """

    chunks = []

    current_text = ""
    current_page = None
    current_heading = None

    chunk_index = 0

    def save_current_chunk():

        nonlocal current_text
        nonlocal current_page
        nonlocal current_heading
        nonlocal chunk_index

        text = current_text.strip()

        if len(text) < MIN_CHUNK_SIZE:
            return

        metadata = {}

        if current_heading:
            metadata["heading"] = current_heading

        chunks.append({
            "chunk_index": chunk_index,
            "page_number": current_page,
            "text": text,
            "metadata": metadata
        })

        chunk_index += 1

    for page in pages:

        page_number = page["page_number"]
        page_text = page["text"]

        # Split into paragraphs first.
        paragraphs = re.split(
            r"\n\s*\n",
            page_text
        )

        for paragraph in paragraphs:

            paragraph = paragraph.strip()

            if not paragraph:
                continue

            # Inspect individual lines for possible headings.
            lines = paragraph.splitlines()

            if len(lines) == 1 and looks_like_heading(
                lines[0]
            ):
                current_heading = lines[0].strip()
                continue

            paragraph = " ".join(
                line.strip()
                for line in lines
                if line.strip()
            )

            if not paragraph:
                continue

            if current_page is None:
                current_page = page_number

            # If adding the paragraph would make the chunk
            # too large, save the current chunk first.
            if (
                current_text
                and len(current_text) + len(paragraph) + 1
                > TARGET_CHUNK_SIZE
            ):

                save_current_chunk()

                # Preserve a small amount of context from
                # the previous chunk.
                overlap_text = current_text[
                    -OVERLAP:
                ].strip()

                current_text = overlap_text

                current_page = page_number

            if current_text:
                current_text += "\n\n"

            current_text += paragraph

    # Save final chunk
    save_current_chunk()

    return chunks


# =========================================================
# PDF INGESTION
# =========================================================

def extract_text_from_pdf(
    file,
    db: Session,
    pdf_id: int
):
    """
    Extract, chunk, embed and store a PDF.
    """

    print("\n" + "=" * 60)
    print("PROCESSING PDF")
    print("PDF ID:", pdf_id)
    print("=" * 60)

    # -----------------------------------------------------
    # Extract pages
    # -----------------------------------------------------

    pages = extract_pdf_pages(file)

    if not pages:
        print("WARNING: No text could be extracted.")
        return 0

    total_text = sum(
        len(page["text"])
        for page in pages
    )

    print("Pages with text:", len(pages))
    print("Extracted text length:", total_text)

    # -----------------------------------------------------
    # Create chunks
    # -----------------------------------------------------

    chunks = create_chunks(pages)

    print("Number of chunks:", len(chunks))

    if not chunks:
        print("WARNING: No useful chunks created.")
        return 0

    # -----------------------------------------------------
    # Prepare embedding text
    # -----------------------------------------------------

    embedding_inputs = []

    for chunk in chunks:

        metadata = chunk["metadata"]

        heading = metadata.get(
            "heading",
            ""
        )

        # Give the embedding model document context.
        #
        # This is generated from the actual document,
        # not from hardcoded textbook knowledge.
        if heading:
            embedding_text = (
                f"Heading: {heading}\n\n"
                f"{chunk['text']}"
            )
        else:
            embedding_text = chunk["text"]

        embedding_inputs.append(
            embedding_text
        )

    # -----------------------------------------------------
    # Generate embeddings
    # -----------------------------------------------------

    embeddings = model.encode(
        embedding_inputs,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    # -----------------------------------------------------
    # Store chunks
    # -----------------------------------------------------

    for chunk, embedding in zip(
        chunks,
        embeddings
    ):

        db_chunk = PDFChunk(
            pdf_id=pdf_id,

            chunk_text=chunk["text"],

            embedding=json.dumps(
                embedding.tolist()
            ),

            page_number=chunk["page_number"],

            chunk_index=chunk["chunk_index"],

            chunk_metadata=chunk["metadata"]
        )

        db.add(db_chunk)

    db.commit()

    print(
        "PDF ingestion completed successfully."
    )

    return len(chunks)


# =========================================================
# QUERY EMBEDDING
# =========================================================

def create_query_embedding(
    question: str
):
    """
    Convert the user's question into an embedding.
    """

    embedding = model.encode(
        [question],
        normalize_embeddings=True,
        show_progress_bar=False
    )[0]

    return embedding


# =========================================================
# PDF SEARCH
# =========================================================

def search_chunks(
    question: str,
    db: Session,
    pdf_id: int,
    top_k: int = TOP_K
):
    """
    Retrieve candidate PDF evidence.

    IMPORTANT:
    This function does NOT decide whether the PDF contains
    the final answer.

    It only retrieves the most semantically relevant
    candidates.

    The LLM will make the final reasoning decision.
    """

    print("\n" + "=" * 60)
    print("PDF SEARCH")
    print("PDF ID:", pdf_id)
    print("Question:", question)
    print("=" * 60)

    # -----------------------------------------------------
    # Query embedding
    # -----------------------------------------------------

    query_embedding = create_query_embedding(
        question
    )

    # -----------------------------------------------------
    # Get chunks belonging ONLY to this PDF
    # -----------------------------------------------------

    pdf_chunks = (
        db.query(PDFChunk)
        .filter(
            PDFChunk.pdf_id == pdf_id
        )
        .all()
    )

    if not pdf_chunks:

        return {
            "context": "",
            "score": 0.0,
            "relevant": False,
            "candidates": []
        }

    results = []

    # -----------------------------------------------------
    # Semantic similarity
    # -----------------------------------------------------

    for chunk in pdf_chunks:

        embedding = np.array(
            json.loads(
                chunk.embedding
            ),
            dtype=np.float32
        )

        semantic_score = float(
            np.dot(
                query_embedding,
                embedding
            )
        )

        results.append({
            "score": semantic_score,
            "chunk": chunk
        })

    # -----------------------------------------------------
    # Sort
    # -----------------------------------------------------

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    # -----------------------------------------------------
    # Debug
    # -----------------------------------------------------

    print("\nTop PDF candidates:")

    for result in results[:top_k]:

        chunk = result["chunk"]

        print(
            round(result["score"], 4),
            "| page:",
            chunk.page_number,
            "| chunk:",
            chunk.chunk_index,
            "|",
            chunk.chunk_text[:100]
                .replace("\n", " ")
        )

    # -----------------------------------------------------
    # Candidate chunks
    # -----------------------------------------------------

    candidates = []

    for result in results[:top_k]:

        chunk = result["chunk"]

        candidates.append({
            "score": result["score"],
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "text": chunk.chunk_text,
            "metadata": chunk.chunk_metadata or {}
        })

    # -----------------------------------------------------
    # Build context
    # -----------------------------------------------------

    context_parts = []

    for candidate in candidates:

        metadata = candidate["metadata"]

        heading = metadata.get(
            "heading"
        )

        header = (
            f"[Page {candidate['page_number']}]"
        )

        if heading:
            header += (
                f"\n[Heading: {heading}]"
            )

        context_parts.append(
            f"{header}\n"
            f"{candidate['text']}"
        )

    context = "\n\n---\n\n".join(
        context_parts
    )

    # -----------------------------------------------------
    # IMPORTANT
    # -----------------------------------------------------
    #
    # We intentionally DO NOT use a hardcoded threshold such
    # as:
    #
    # if score >= 0.32:
    #
    # Retrieval gives candidates.
    #
    # The LLM decides whether the candidates actually answer
    # the user's question.
    # -----------------------------------------------------

    best_score = candidates[0]["score"]

    return {
        "context": context,
        "score": best_score,
        "relevant": True,
        "candidates": candidates
    }