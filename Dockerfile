# syntax=docker/dockerfile:1
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better cache)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 5000

# ✅ Correct multi-line ENV (one var per line)
ENV FLASK_SECRET=dev-secret-change-me \
    OLLAMA_HOST=http://ollama:11434 \
    CHAT_MODEL=llama3.2:3b \
    EMBEDDING_MODEL=nomic-embed-text \
    COLLECTION_NAME=company_knowledge_base

CMD ["python", "app.py"]
