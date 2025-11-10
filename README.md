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
# Загрузить файл и задать вопрос через терминал
curl -sS -X POST http://127.0.0.1:8000/index \
  -F "file=@/полный/путь/к/договору.docx"    # ожидается ответ вида {"file_id":"a51abe27-35b2-4ce8-9be2-535f8..."}

curl -sS -X POST http://127.0.0.1:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "a51abe27-35b2-4ce8-9be2-535f8...",
    "question": "Укажи предмет договора"
  }'

