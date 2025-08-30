import os
import re
import glob
from typing import List
from dotenv import load_dotenv
from tqdm import tqdm

from pypdf import PdfReader
import docx

from rag import get_collection, get_client, OllamaEmbeddingFunction

load_dotenv()

DATA_DIR = os.path.join(os.getcwd(), "sample_data")
SUPPORTED_EXTS = (".txt", ".md", ".pdf", ".docx")

# ------------------------------ Text Loading --------------------------------
def read_text_from_file(path: str) -> str:
    pl = path.lower()
    if pl.endswith((".txt", ".md")):
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    if pl.endswith(".pdf"):
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    if pl.endswith(".docx"):
        d = docx.Document(path)
        return "\n".join(p.text for p in d.paragraphs)
    raise ValueError(f"Unsupported file type: {path}")

# ------------------------------ Chunking ------------------------------------
def clean_text(s: str) -> str:
    s = s.replace("\x00", " ")
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def chunk_text(text: str, chunk_chars: int = 900, overlap: int = 150) -> List[str]:
    text = clean_text(text)
    if not text:
        return []
    chunks, start = [], 0
    while start < len(text):
        end = min(start + chunk_chars, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks

# ------------------------------ Ingest --------------------------------------
def ingest_folder(folder: str = DATA_DIR):
    # Recreate collection to avoid duplicates
    client = get_client()
    try:
        client.delete_collection("company_knowledge_base")
    except Exception:
        pass
    col = client.create_collection(
        name="company_knowledge_base",
        metadata={"hnsw:space": "cosine"}
    )

    files = []
    for ext in SUPPORTED_EXTS:
        files.extend(glob.glob(os.path.join(folder, f"*{ext}")))
    if not files:
        print(f"No files found in {folder}. Add .txt/.md/.pdf/.docx and re-run.")
        return

    ids, docs, metas = [], [], []
    for fp in files:
        base = os.path.basename(fp)
        text = read_text_from_file(fp)
        chunks = chunk_text(text)
        for i, ch in enumerate(chunks):
            ids.append(f"{base}::{i}")
            docs.append(ch)
            metas.append({"source": base, "chunk": i})

    print(f"Embedding + adding {len(docs)} chunks...")
    ef = OllamaEmbeddingFunction()
    B = 64
    for i in tqdm(range(0, len(docs), B)):
        batch_docs = docs[i:i+B]
        batch_ids = ids[i:i+B]
        batch_meta = metas[i:i+B]
        batch_embs = ef(batch_docs)
        col.add(ids=batch_ids, documents=batch_docs, metadatas=batch_meta, embeddings=batch_embs)

    print("Done. You can now run the Flask app and ask questions.")

if __name__ == "__main__":
    ingest_folder()
