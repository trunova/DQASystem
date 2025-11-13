from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from .settings import settings
from .models import (
    FileUploadResponse, QuestionCreate, QuestionResponse,
    AnswerResponse, AnswerReference
)
from .store import (
    create_file, get_file_dir, create_question, set_answer, set_error, get_question
)
from .rag import ingest_docx_to_chroma, answer_rag, answer_stuff
from .llm import get_llm
from pathlib import Path

app = FastAPI(title="Document question answering", version="1.1.0")

llm = get_llm()

@app.post("/files", response_model=FileUploadResponse, tags=["upload"])
async def upload_file(bg: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Требуется файл .docx")

    file_id = str(uuid.uuid4())
    file_dir = Path(settings.STORAGE_DIR) / file_id
    file_dir.mkdir(parents=True, exist_ok=True)

    dst_path = file_dir / "uploaded.docx"
    with dst_path.open("wb") as f:
        f.write(await file.read())

    created_id = create_file(str(file_dir), id=file_id)

    def _build():
        try:
            ingest_docx_to_chroma(file_id, str(dst_path))
        except Exception as e:
            print(f"[indexing error] {e}")


    bg.add_task(_build)
    return FileUploadResponse(file_id=created_id)


def _process_question(question_id: str, file_id: str, question: str, mode: str):
    try:
        file_dir = get_file_dir(file_id)
        if not file_dir:
            set_error(question_id, "Файл не найден")
            return
        if mode == "stuff":
            ans, refs = answer_stuff(file_dir, question, llm)
        else:
            ans, refs = answer_rag(file_dir, question, llm)
        set_answer(question_id, ans, [{"rank": i + 1, "snippet": s} for i, s in enumerate(refs)])
    except Exception as e:
        set_error(question_id, f"Ошибка при обработке вопроса: {e}")


@app.post("/questions", response_model=QuestionResponse)
async def ask_question(payload: QuestionCreate, bg: BackgroundTasks):
    file_dir = get_file_dir(payload.file_id)
    if not file_dir:
        raise HTTPException(status_code=404, detail="file_id не существует")

    mode = (getattr(payload, "mode", "rag") or "rag").lower()
    if mode not in ("rag", "stuff"):
        mode = "rag"

    qid = create_question(payload.file_id, payload.question, mode)

    _process_question(qid, payload.file_id, payload.question, mode)

    return QuestionResponse(question_id=qid)


@app.get("/answers/{question_id}", response_model=AnswerResponse, tags=["qa"])
def get_answer(question_id: str):
    row = get_question(question_id)
    if not row:
        raise HTTPException(status_code=404, detail="question_id не существует")

    if row.status == "PENDING":
        return AnswerResponse(status=row.status, answer=None, references=None)

    references = None
    if row.refs_json:
        try:
            loaded = json.loads(row.refs_json)
            references = [AnswerReference(**item) for item in loaded]
        except Exception:
            references = None

    return AnswerResponse(status=row.status, answer=row.answer, references=references)
