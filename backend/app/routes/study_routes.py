from fastapi import APIRouter

from app.services.tutor_service import analyze_session

router = APIRouter()


@router.get("/session-result/{session_id}")
def session_result(session_id: str):
    return analyze_session(session_id)