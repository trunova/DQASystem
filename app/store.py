# app/store.py
import uuid
import json
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, create_engine, Session
from .models import FileRow, QuestionRow

_engine = create_engine("sqlite:///storage/app.db", connect_args={"check_same_thread": False})
SQLModel.metadata.create_all(_engine)

def new_session():
    return Session(_engine)

def create_file(dir_path: str, *, id: str | None = None) -> str:
    with Session(_engine) as s:
        row = FileRow(id=id or str(uuid.uuid4()), dir=dir_path)
        s.add(row)
        s.commit()
        s.refresh(row)
        return row.id

def get_file_dir(file_id: str) -> Optional[str]:
    with Session(_engine) as s:
        row = s.get(FileRow, file_id)
        return row.dir if row else None

def create_question(file_id: str, text: str) -> str:
    with Session(_engine) as s:
        q = QuestionRow(file_id=file_id, question=text)
        s.add(q)
        s.commit()
        s.refresh(q)
        return q.id

def set_answer(question_id: str, answer: str, references: List[Dict[str, Any]]):
    with Session(_engine) as s:
        row = s.get(QuestionRow, question_id)
        if not row:
            return
        row.status = "DONE"
        row.answer = answer
        row.refs_json = json.dumps(references, ensure_ascii=False)
        s.add(row)
        s.commit()

def set_error(question_id: str, msg: str):
    with Session(_engine) as s:
        row = s.get(QuestionRow, question_id)
        if not row:
            return
        row.status = "ERROR"
        row.answer = msg[:2000]
        row.refs_json = None
        s.add(row)
        s.commit()

def get_question(question_id: str) -> Optional[QuestionRow]:
    with Session(_engine) as s:
        return s.get(QuestionRow, question_id)
