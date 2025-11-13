# Document QA 


## Quick start
```bash
docker compose up -d --build

# Скачать модель в Ollama
docker compose exec ollama ollama pull qwen3:30b-instruct
# Или в контейнере 
curl -X POST http://ollama:11434/api/pull -H "Content-Type: application/json" -d '{"name":"qwen3:30b-instruct"}'

# SwaggerUI: http://localhost:8000/docs
# Загрузить файл и задать вопрос через терминал
curl -s -X POST "http://localhost:8000/files" -F "file=@/полный/путь/к/договору.docx" # ожидается ответ вида {"file_id":"a51abe27-35b2-4ce8-9be2-535f8..."}

# mode: ["rag", "stuff"], в режиме rag - обработка документа по чанкам, 
# в stuff - в качестве контекста подаётся весь документ
curl -s -X POST http://localhost:8000/questions -H 'Content-Type: application/json' -d '{"file_id":"a51abe27-35b2-4ce8-9be2-535f8...","question":"Укажи предмет договора","mode":"rag"}'

curl -s -X POST http://localhost:8000/questions -H 'Content-Type: application/json' -d '{"file_id":"a51abe27-35b2-4ce8-9be2-535f8...","question":"Укажи предмет договора","mode":"stuff"}'

# ожидается ответ вида {"question_id":"bb5cee44-6052-4158-a5d..."}

# Посмотреть ответ
curl -s "http://localhost:8000/answers/bb5cee44-6052-4158-a5d..." | jq


