from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, func

from app.database import Base


class LearningTopic(Base):
    __tablename__ = "learning_topics"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    session_id = Column(
        Integer,
        ForeignKey(
            "chat_sessions.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    pdf_id = Column(
        Integer,
        ForeignKey(
            "pdfs.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    topic = Column(
        String(255),
        nullable=False
    )

    first_discussed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    last_discussed_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    discussion_count = Column(
        Integer,
        default=1,
        nullable=False
    )