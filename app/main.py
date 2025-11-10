import os
import json
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles

from .settings import settings
from .models import (
    FileUploadResponse, QuestionCreate, QuestionResponse,
    AnswerResponse, AnswerReference
)
from .store import (
    create_file, get_file_dir, create_question, set_answer, set_error, get_question
)
from .rag import build_index_from_docx, answer_question
from .llm import get_llm_client
from .es import ensure_index

app = FastAPI(title="Document question answering", version="1.1.0")
llm = get_llm_client()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/files", response_model=FileUploadResponse)
async def upload_file(bg: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Требуется файл .docx")

    file_id = str(uuid.uuid4())

    tmp_path = Path(settings.STORAGE_DIR) / f"tmp_{file_id}.docx"
    with tmp_path.open("wb") as f:
        f.write(await file.read())

    file_dir = Path(settings.STORAGE_DIR) / file_id
    file_dir.mkdir(parents=True, exist_ok=True)
    dst_path = file_dir / "uploaded.docx"
    tmp_path.replace(dst_path)

    created_id = create_file(str(file_dir), id=file_id)

    def _build():
        try:
            ensure_index(file_id)
            build_index_from_docx(file_id, str(dst_path))
        except Exception as e:
            print(f"[indexing error] {e}")

    bg.add_task(_build)
    return FileUploadResponse(file_id=created_id)

def _wait_index_ready(file_dir: str, timeout_sec: int = 120) -> bool:
    idx = Path(file_dir) / "faiss_index" / "index.faiss"
    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if idx.exists() and idx.stat().st_size > 0:
            return True
        time.sleep(0.5)
    return False

def _process_question(question_id: str, file_id: str, question: str):
    try:
        file_dir = get_file_dir(file_id)
        if not file_dir:
            set_error(question_id, "Файл не найден")
            return

        _wait_index_ready(file_dir, timeout_sec=120)

        ans, refs = answer_question(file_dir, question, llm)
        set_answer(question_id, ans, refs)
    except Exception as e:
        set_error(question_id, f"Ошибка при обработке вопроса: {e}")

@app.post("/questions", response_model=QuestionResponse)
async def ask_question(payload: QuestionCreate, bg: BackgroundTasks):
    file_dir = get_file_dir(payload.file_id)
    if not file_dir:
        raise HTTPException(status_code=404, detail="file_id не существует")

    qid = create_question(payload.file_id, payload.question)
    bg.add_task(_process_question, qid, payload.file_id, payload.question)
    return QuestionResponse(question_id=qid)

@app.get("/answers/{question_id}", response_model=AnswerResponse)
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

# http://localhost:8000/ui/
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="ui")

@app.get("/llm_selftest")
def llm_selftest():
    try:
        text = llm.generate("Ответь одним словом: тест")
        return {"ok": True, "model": os.getenv("OLLAMA_MODEL", settings.OLLAMA_MODEL), "response": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}
