from pydantic import BaseModel
from typing import Optional, List, Dict , Any

class SearchRequest(BaseModel):
    session_id: Optional[str] = None
    domain : str 

class AnswersRequest(BaseModel):
    session_id: str
    answers: Dict[str,Any]

class SenderProfileRequest(BaseModel):
    session_id: str
    name: str
    college: str
    degree: str
    year: str
    skills: List[str]
    project: str
    achieve: str
    linkedin: str
    goal: str

class SessionResponse(BaseModel):
    session_id: str
    step: str
    data: Dict[str, Any]
    logs: List[Dict[str, str]]
    error: Optional[str] = None