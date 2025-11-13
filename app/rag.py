from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import List, Tuple

from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from .settings import settings
import time

# --------------------- очистка текста ---------------------

_RE_SOFT = re.compile(r"[\u00AD\u200B\u200C\u200D]")    
_RE_MULTI_WS = re.compile(r"\s{2,}")
_RE_WATERMARK = re.compile(r"ОГРАЖДАЮЩАЯ\s+АКТУАЛЯЦИЯ", re.IGNORECASE)
_RE_ANY_NL = re.compile(r"(?:\r\n|\r|\n|\\r\\n|\\n|\\r)+")
_RE_CTRL   = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

_ROLE_MAP: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bпоставщик\w*\b", re.I), "исполнитель"),
    (re.compile(r"\bпродавец\w*\b", re.I), "исполнитель"),
    (re.compile(r"\bподрядчик\w*\b", re.I), "исполнитель"),
    (re.compile(r"\bпокупател\w*\b", re.I), "заказчик"),
    (re.compile(r"\bклиент\w*\b", re.I), "заказчик"),
]

def _strip_weird(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\xa0", " ")
    s = _RE_SOFT.sub("", s)
    return s

def _clean_block(s: str) -> str:
    s = _strip_weird(s)
    s = _RE_ANY_NL.sub(" ", s)
    s = _RE_CTRL.sub(" ", s)
    s = _RE_MULTI_WS.sub(" ", s)
    return s.strip()

def _drop_watermark_tail(text: str) -> str:
    if len(_RE_WATERMARK.findall(text)) >= 5:
        m = _RE_WATERMARK.search(text)
        if m:
            return text[:m.start()]
    return text

def _expand_query(q: str) -> str:
    extras = []
    low = q.lower()
    for pat, canon in _ROLE_MAP:
        if pat.search(low):
            extras.append(canon)
    if extras:
        q = f"{q} " + " ".join(sorted(set(extras)))
    return q

def _strip_tables(s: str) -> str:
    s = re.sub(r'(\| )*', '', s)
    s = re.sub(r'\|\\n\d+', '', s)
    s = re.sub(r'(\|---)*', '', s)
    s = re.sub(r'\|*', '', s)
    s = re.sub(r'\\n', ' ', s)
    s = re.sub(r'_+', '', s)
    return s

def _finalize_answer(text: str, max_chars: int = 300) -> str:
    s = re.sub(r"\s+", " ", (text or "")).strip()
    if "В документе не найдено" in s:
        return "В документе не найдено"
    parts = re.split(r"(?<=[.!?])\s+", s)
    s = " ".join(parts[:2]).strip()
    if len(s) > max_chars:
        s = s[:max_chars].rsplit(" ", 1)[0] + "…"
    return s or "В документе не найдено"


# -------------- Embeddings --------------

def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name=settings.EMBED_MODEL,            
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

def _text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,             
        chunk_overlap=settings.CHUNK_OVERLAP,       
        separators=["\n\n", "\n", " ", ""],       
    )

# -------------- Индексация --------------

def ingest_docx_to_chroma(file_id: str, path: str) -> str:
    base = Path(settings.STORAGE_DIR) / file_id
    base.mkdir(parents=True, exist_ok=True)

    raw_docs = Docx2txtLoader(path).load()  
    if not raw_docs:
        raise RuntimeError("Пустой документ")

    joined = " ".join(_clean_block(d.page_content) for d in raw_docs)
    joined = _drop_watermark_tail(joined)
    joined = _strip_tables(joined)
    (base / "document.txt").write_text(joined, encoding="utf-8")

    splitter = _text_splitter()
    chunks: List[Document] = splitter.split_documents([Document(page_content=joined)])

    def _is_noisy(txt: str) -> bool:
        if not txt:
            return True
        alpha = sum(ch.isalpha() for ch in txt)
        if alpha / max(1, len(txt)) < 0.2:
            return True
        toks = [t for t in re.split(r"\W+", txt) if t]
        if not toks:
            return True
        from collections import Counter
        _, cnt = Counter(toks).most_common(1)[0]
        return cnt >= max(6, int(len(toks) * 0.6))

    chunks = [Document(page_content=c.page_content) for c in chunks if not _is_noisy(c.page_content)]

    emb = get_embeddings()
    Chroma.from_documents(
        documents=chunks,
        embedding=emb,
        persist_directory=str(base / "chroma"),
    ).persist()

    return str(base)


def _load_chroma(file_dir: str) -> Chroma:
    emb = get_embeddings()
    return Chroma(
        persist_directory=str(Path(file_dir) / "chroma"),
        embedding_function=emb,
    )

# ------------- Промпты -------------


QA_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        (
            "Ты — помощник по русскоязычным договорам. Тебе передают полный текст договора.\n"
            "Твоя задача — КРАТКО отвечать на вопросы по тексту.\n\n"
            "Строгие правила:\n"
            "1) Отвечай ТОЛЬКО по тексту договора, ничего не выдумывай.\n"
            "2) НЕ переписывай, НЕ дополняй и НЕ исправляй договор или акты, "
            "НЕ генерируй шаблоны документов.\n"
            "3) НЕ используй вводные фразы вроде «на основе текста», «судя по документу» и т.п.\n"
            "4) Ответ должен быть одним–двумя короткими предложениями, СРАЗУ по сути вопроса.\n"
            "5) Если ответа нет в тексте, верни ровно: В документе не найдено.\n"
            "6) Верни только текст ответа, без пояснений, перечислений и форматирования Markdown."
        ),
    ),
    (
        "user",
        (
            "Вопрос: {question}\n\n"
            "Контекст (текст договора):\n"
            "{context}\n\n"
            "Ответь одним кратким предложением строго по сути вопроса."
        ),
    ),
])


RAG_PROMPT = ChatPromptTemplate.from_template(
    "Ты — помощник по русскоязычным договорам. Используй приведённый контекст. "
    "Если ответа нет в контексте — ответь: \"В документе не найдено\". Отвечай кратко.\n\n"
    "Вопрос: {question}\n\nКонтекст:\n{context}"
)


# -------------- Ответ: RAG --------------

def format_docs(docs: List[Document]) -> str:
    text = "\n---\n".join(d.page_content.strip() for d in docs if d.page_content)
    return text[: settings.CONTEXT_CHARS_LIMIT]

def answer_rag(file_dir: str, question: str, llm) -> Tuple[str, List[str]]:
    print("[answer_rag] start")
    chroma = _load_chroma(file_dir)
    print("[answer_rag] after _load_chroma")

    retriever = chroma.as_retriever(
        search_type="mmr",
        search_kwargs={"k": settings.RETRIEVAL_K, "fetch_k": settings.RETRIEVAL_FETCH_K},
    )

    qx = _expand_query(question)
    print("[answer_rag] before chain building")
    chain = (
        {
            "question": RunnablePassthrough(),
            "context": retriever | RunnableLambda(format_docs),
        }
        | RAG_PROMPT
        | llm
        | StrOutputParser()
    )
    print("[answer_rag] before chain.invoke")
    t0 = time.time()
    answer = chain.invoke(qx).strip()
    t1 = time.time()
    print(f"[answer_rag] after chain.invoke, took {t1 - t0:.1f}s")

    docs = retriever.invoke(qx) or []
    refs = []
    for d in docs:
        snip = (d.page_content or "").strip().replace("\n", " ")
        if snip:
            refs.append(snip[:400])

    return answer, refs



# --------------------- Ответ: Stuff  ---------------------

def answer_stuff(file_dir: str, question: str, llm):
    full_path = Path(file_dir) / "document.txt"
    context = full_path.read_text(encoding="utf-8") if full_path.exists() else ""

    chain = QA_PROMPT | llm | StrOutputParser()
    raw = chain.invoke({"question": question, "context": context})

    answer = _finalize_answer(raw)
    refs = [context[:400].replace("\n", " ")] if context else []
    return answer, refs

