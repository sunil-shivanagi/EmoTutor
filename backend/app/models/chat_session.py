from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    pdf_id = Column(
        Integer,
        ForeignKey(
            "pdfs.id",
            ondelete="SET NULL"
        ),
        nullable=True
    )

    current_topic_id = Column(
        Integer,
        ForeignKey(
            "learning_topics.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    title = Column(
        String,
        default="New Chat"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )