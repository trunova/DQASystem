from pathlib import Path
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    STORAGE_DIR: str = "storage"

    EMBED_MODEL: str = "intfloat/multilingual-e5-small"

    LLM_TEMPERATURE: float = 0.0
    LLM_NUM_CTX: int = 12000 #262144
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "qwen3:30b-instruct" #"qwen3:30b-instruct"
    MAX_TOKENS: int = 256

    CHUNK_SIZE: int = 700
    CHUNK_OVERLAP: int = 100
    CONTEXT_CHARS_LIMIT: int = 4000
    RETRIEVAL_K: int = 6
    RETRIEVAL_FETCH_K: int = 24

    class Config:
        env_file = ".env"

settings = Settings()
Path(settings.STORAGE_DIR).mkdir(parents=True, exist_ok=True)
