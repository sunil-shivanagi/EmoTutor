from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.sql import func

from app.database import Base


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    session_id = Column(
        Integer,
        ForeignKey("chat_sessions.id")
    )

    question = Column(Text)

    answer = Column(Text)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )