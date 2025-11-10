from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    STORAGE_DIR: str = "storage"

    EMBED_MODEL: str = "intfloat/multilingual-e5-small" 

    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "qwen2.5:3b-instruct-q4_0"

    MAX_TOKENS: int = 256
    LLM_TEMPERATURE: float = 0.0
    LLM_NUM_CTX: int = 2048
    LLM_NUM_GPU: int = 0

    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    CONTEXT_CHARS_LIMIT: int = 3500
    RETRIEVAL_K: int = 6
    RETRIEVAL_FETCH_K: int = 24
    RETRIEVAL_MMR_LAMBDA: float = 0.6

    ES_HOST: str = "http://elasticsearch:9200"
    ES_INDEX_PREFIX: str = "docs_chunks"
    ANNOTATE_LIMIT: int = 10      
    ANNOTATE_ENABLED: bool = True  

    class Config:
        env_file = ".env"

settings = Settings()
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
