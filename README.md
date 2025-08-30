# Flask RAG Chatbot (Local Ollama + Your Company Docs)

A minimal, **easy-to-run** Retrieval-Augmented Generation (RAG) chatbot project using:
- **Flask** for the web app
- **Ollama** (local LLM + embeddings) — no cloud keys needed
- **Chroma** as a local vector database
- **Your PDF/DOCX/TXT files** for private, personalized answers

---

## 0) Prerequisites

- Python 3.10+
- [Ollama](https://ollama.com) installed and running
- Git (optional)

Pull the small open-source models we use here:

```bash
# Start Ollama if not running (Windows & macOS: installed app; Linux: `ollama serve`)
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

> You can swap `CHAT_MODEL` and `EMBEDDING_MODEL` later in `.env` (e.g., `mistral:7b`, `qwen2.5:3b`, etc.).

---

## 1) Create a virtual environment & install deps

**Windows (PowerShell):**
```powershell
cd ai-flask-rag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
cd ai-flask-rag
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## 2) Add your company documents

Drop your files into `sample_data/`. Supported now: **.txt, .pdf, .docx, .md**

Some example files are already there.

---

## 3) Build the vector index (ingest)

```bash
python ingest.py
```

This:
- Reads and chunks your docs
- Generates embeddings via Ollama (`EMBEDDING_MODEL` from `.env`)
- Saves a persistent Chroma collection in `./chroma_db`

Re-run this whenever you add/update files.

---

## 4) Run the Flask app

```bash
python app.py
```

Then open **http://127.0.0.1:5000** in your browser.

---

## 5) Ask questions!

The chatbot will:
- Retrieve the most relevant passages from your docs
- Use the LLM (`CHAT_MODEL`) to answer
- Show the sources it used

---

## Tips

- If Ollama is on a different host/port, change `OLLAMA_HOST` in `.env`.
- To change models, edit `.env` or set env vars before running:
  - `CHAT_MODEL`, `EMBEDDING_MODEL`
- To rebuild the index after docs change: `python ingest.py`

---

## Project Layout

```
ai-flask-rag/
├─ app.py                # Flask web server
├─ ingest.py             # One-time (or repeat) document ingestion to Chroma
├─ rag.py                # RAG helper (embeddings, retrieval, LLM chat)
├─ templates/
│  └─ index.html         # Simple chat UI
├─ static/
│  └─ styles.css         # Minimal CSS
├─ sample_data/
│  ├─ 00_welcome.txt
│  ├─ hr_policy_example.txt
│  └─ product_faq.md
├─ requirements.txt
├─ .env
└─ README.md
```

Enjoy!

---

# Run with Docker (Windows/macOS/Linux with Docker Desktop)

## 1) Start the stack (Ollama + Flask app)
From the `ai-flask-rag` folder:
```bash
docker compose up -d --build
```

This launches:
- `ollama` at http://127.0.0.1:11434
- `ai-flask-rag` at http://127.0.0.1:5000

> First time may take a bit because images and Python packages are downloaded.

## 2) Pull models *inside* the Ollama container
Open a shell in the Ollama container and pull the models:
```bash
docker compose exec ollama ollama pull llama3.2:3b
docker compose exec ollama ollama pull nomic-embed-text
```
(You can choose different models later—just update `.env` or compose env overrides.)

## 3) Ingest your docs (build the vector DB)
Run the ingestion script inside the app container:
```bash
docker compose exec app python ingest.py
```
This reads files from `./sample_data` (mounted into the container) and writes the Chroma DB into `./chroma_db` on your host.

## 4) Use the web app
Open: http://127.0.0.1:5000

Ask questions. Answers will be grounded with citations from your documents.

## 5) Update docs? Re-ingest.
Copy new/updated files into `sample_data/` then run:
```bash
docker compose exec app python ingest.py
```

## 6) Change models or settings
- Edit `.env` (already mounted into the container)
- Or override at run time, e.g.:
```bash
CHAT_MODEL=mistral:7b EMBEDDING_MODEL=nomic-embed-text docker compose up -d --build
```

## 7) Stop and clean
```bash
docker compose down
# (Keeps your local volumes: ollama cache, chroma_db, sample_data)
# To nuke everything including volumes:
# docker compose down -v
```

**Troubleshooting**
- If `app` starts before `ollama` is ready, the healthcheck will retry. Give it a moment.
- If a request says “connection refused to /api/embeddings,” ensure the models are pulled (Step 2).
- On Windows, ensure file sharing is allowed for the drive containing this project (Docker Desktop > Settings > Resources > File Sharing).
