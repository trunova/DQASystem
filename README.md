# Document QA 


## Quick start
```bash
docker compose up -d --build

# Один раз скачать модель в Ollama
docker compose exec ollama ollama pull qwen3:30b-instruct
# Или в контейнере 
curl -X POST http://ollama:11434/api/pull -H "Content-Type: application/json" -d '{"name":"qwen3:30b-instruct"}'

# Проверка
docker compose ps
curl -fsS http://localhost:8000/health   # ожидается {"status":"ok"}

# Открыть UI
# В браузере перейти на: http://localhost:8000/ui/
