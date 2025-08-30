import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv

import chromadb
from chromadb.config import Settings

load_dotenv()

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "company_knowledge_base")

DB_DIR = os.path.join(os.getcwd(), "chroma_db")

# ------------------------------- Embeddings ---------------------------------
class OllamaEmbeddingFunction:
    def __init__(self, model: str = EMBEDDING_MODEL, host: str = OLLAMA_HOST):
        self.model = model
        self.host = host.rstrip("/")

    def __call__(self, texts: List[str]) -> List[List[float]]:
        embs: List[List[float]] = []
        for t in texts:
            resp = requests.post(
                f"{self.host}/api/embeddings",
                json={"model": self.model, "prompt": t},
                timeout=120
            )
            resp.raise_for_status()
            embs.append(resp.json()["embedding"])
        return embs

# ------------------------------- Collection ---------------------------------
def get_client():
    return chromadb.PersistentClient(path=DB_DIR, settings=Settings())

def get_collection(create_if_missing: bool = True):
    client = get_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        if not create_if_missing:
            raise
        return client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )

# ------------------------------- Retrieval ----------------------------------
def retrieve(query: str, top_k: int = 4) -> Dict[str, Any]:
    col = get_collection(create_if_missing=False)
    ef = OllamaEmbeddingFunction()
    qemb = ef([query])[0]
    results = col.query(
        query_embeddings=[qemb],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]  # ← removed "ids"
    )
    out = []
    # ids are still present in `results["ids"]` even if not listed in include
    for i in range(len(results["ids"][0])):
        out.append({
            "id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i],
        })
    return {"results": out}


# ----------------------------- LLM (Ollama) ---------------------------------
SYSTEM_PROMPT = """You are a helpful company assistant. Answer the user's question using ONLY the provided context.
If the answer is not in the context, say you don't have that information.
Be concise and include a short bullet list of sources used.
"""

def format_context(snippets: List[Dict[str, Any]]) -> str:
    lines = []
    for s in snippets:
        src = s["metadata"].get("source", "unknown")
        chunk = s["metadata"].get("chunk", "")
        lines.append(f"[{src}#{chunk}] {s['text']}")
    return "\n\n".join(lines)

def chat_llm(question: str, context_snippets: List[Dict[str, Any]], history: List[Dict[str, str]] = None) -> str:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history[-6:])

    context_text = format_context(context_snippets)
    user_msg = f"Context:\n{context_text}\n\nUser question: {question}\n\nRemember to cite sources as [filename#chunk]."
    messages.append({"role": "user", "content": user_msg})

    resp = requests.post(
        f"{OLLAMA_HOST.rstrip('/')}/api/chat",
        json={"model": CHAT_MODEL, "messages": messages, "stream": False, "options": {"temperature": 0.2}},
        timeout=600
    )
    resp.raise_for_status()
    return resp.json().get("message", {}).get("content", "").strip()
