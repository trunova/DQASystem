import uuid
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as ORMField

class FileUploadResponse(BaseModel):
    file_id: str

class QuestionCreate(BaseModel):
    file_id: str
    question: str = Field(min_length=3)

class QuestionResponse(BaseModel):
    question_id: str

class AnswerReference(BaseModel):
    rank: int
    snippet: str

class AnswerResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    references: Optional[List[AnswerReference]] = None

class FileRow(SQLModel, table=True):
    id: str = ORMField(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    dir: str  

class QuestionRow(SQLModel, table=True):
    id: str = ORMField(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    file_id: str
    question: str
    status: str = "PENDING"  
    answer: Optional[str] = None
    refs_json: Optional[str] = None
    created_at: datetime = ORMField(default_factory=datetime.utcnow)
