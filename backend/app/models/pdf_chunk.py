from sqlalchemy import Column, Integer, Text, ForeignKey, JSON

from app.database import Base


class PDFChunk(Base):
    __tablename__ = "pdf_chunks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    pdf_id = Column(
        Integer,
        ForeignKey("pdfs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Actual text used by the LLM
    chunk_text = Column(
        Text,
        nullable=False
    )

    # Embedding stored as JSON for now.
    # We can migrate this to pgvector later.
    embedding = Column(
        Text,
        nullable=False
    )

    # Where the chunk came from
    page_number = Column(
        Integer,
        nullable=True
    )

    # Position of this chunk within the PDF
    chunk_index = Column(
        Integer,
        nullable=False
    )

    # Automatically extracted document information.
    # Example:
    # {
    #     "document_title": "...",
    #     "heading": "...",
    #     "section": "..."
    # }
    chunk_metadata = Column(
        JSON,
        nullable=True
    )