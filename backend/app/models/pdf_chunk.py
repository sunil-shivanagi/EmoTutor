from sqlalchemy import Column, Integer, Text, ForeignKey

from app.database import Base


class PDFChunk(Base):
    __tablename__ = "pdf_chunks"

    id = Column(Integer, primary_key=True, index=True)

    pdf_id = Column(Integer, ForeignKey("pdfs.id"))

    chunk_text = Column(Text)

    embedding = Column(Text)