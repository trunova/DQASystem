import os
import httpx
from .settings import settings

class OllamaClient:
    def __init__(self):
        self.base = os.getenv("OLLAMA_BASE_URL", settings.OLLAMA_BASE_URL)
        self.model = os.getenv("OLLAMA_MODEL", settings.OLLAMA_MODEL)
        self.max_tokens = getattr(settings, "MAX_TOKENS", 256)
        self.temperature = getattr(settings, "LLM_TEMPERATURE", 0.0)
        self.num_ctx = getattr(settings, "LLM_NUM_CTX", 1024)
        self.num_gpu = getattr(settings, "LLM_NUM_GPU", 0)

    def generate(self, prompt: str) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
                "num_predict": self.max_tokens,
                "num_gpu": self.num_gpu,
            },
        }
        timeout = httpx.Timeout(400.0, connect=30.0)
        try:
            with httpx.Client(timeout=timeout) as c:
                r = c.post(f"{self.base}/api/generate", json=payload)
                r.raise_for_status()
                data = r.json()
                return (data.get("response") or "").strip()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Ollama HTTP {e.response.status_code}: {e.response.text[:400]}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

def get_llm_client():
    provider = os.getenv("LLM_PROVIDER", settings.LLM_PROVIDER).lower()
    if provider == "ollama":
        return OllamaClient()
    raise RuntimeError(f"Unsupported LLM_PROVIDER: {provider}")
