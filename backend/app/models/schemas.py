from pydantic import BaseModel, EmailStr

# ==============================
# Chat Schemas
# ==============================

class ChatRequest(BaseModel):
    message: str
    emotion: str = "neutral"
    session_id: int | None = None


class ChatResponse(BaseModel):
    reply: str
    plain_text: str
    emotion: str

class CreateSessionRequest(BaseModel):
    pdf_id: int | None = None

# ==============================
# Authentication Schemas
# ==============================

class UserRegister(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    id: int
    full_name: str
    email: EmailStr

    class Config:
        from_attributes = True