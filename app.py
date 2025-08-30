import os
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

from rag import retrieve, chat_llm

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret-change-me")

@app.route("/")
def index():
    return render_template("index.html")

@app.post("/api/chat")
def api_chat():
    data = request.get_json(force=True)
    question = (data or {}).get("question", "").strip()
    if not question:
        return jsonify({"error":"Missing 'question'"}), 400

    # 1) Retrieve relevant context
    retrieved = retrieve(question, top_k=4)["results"]

    # 2) Minimal session-based chat history (LLM memory)
    history = session.get("chat_history", [])
    # 3) Ask the LLM with RAG context
    answer = chat_llm(question, retrieved, history=history)

    # 4) Update history
    history.append({"role":"user", "content": question})
    history.append({"role":"assistant", "content": answer})
    session["chat_history"] = history[-10:]  # keep last 10 turns

    # 5) Return answer + sources
    sources = [f"{r['metadata'].get('source')}#{r['metadata'].get('chunk')}" for r in retrieved]
    return jsonify({"answer": answer, "sources": sources})

if __name__ == "__main__":
    # Run on localhost:5000
    app.run(host="0.0.0.0", port=5000, debug=True)
