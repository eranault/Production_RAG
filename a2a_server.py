from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import uvicorn
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

model = SentenceTransformer('all-MiniLM-L6-v2')
qdrant = QdrantClient(host="localhost", port=6333)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Agent Card ──────────────────────────────────────────────────────────────
# La carte de visite de ton agent — tout agent A2A la lira avant de t'envoyer
# une tâche pour savoir si tu peux l'aider
AGENT_CARD = {
    "name": "hackernews-rag-agent",
    "description": "An AI agent that answers questions about HackerNews stories using semantic search and LLaMA 3",
    "version": "1.0.0",
    "url": "http://localhost:8002",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "skills": [
        {
            "id": "search_hackernews",
            "name": "Search HackerNews",
            "description": "Search HackerNews stories semantically and return AI-generated answers grounded in real stories",
            "inputModes": ["text"],
            "outputModes": ["text"],
            "examples": [
                "What are people saying about AI today?",
                "Are there any stories about Python or open source?"
            ]
        }
    ]
}

@app.get("/.well-known/agent.json")
async def agent_card():
    return JSONResponse(AGENT_CARD)


# ── Pydantic models — définissent le format A2A des requêtes entrantes ───────
class MessagePart(BaseModel):
    text: str

class Message(BaseModel):
    role: str
    parts: List[MessagePart]

class Task(BaseModel):
    id: str
    message: Message


# ── RAG function ─────────────────────────────────────────────────────────────
def search_and_answer(question: str) -> str:
    query_embedding = model.encode(question).tolist()
    result = qdrant.query_points(
        collection_name="hackernews",
        query=query_embedding,
        limit=5
    )
    results = result.points

    if not results:
        return "Sorry, I couldn't find any relevant stories."

    context = "\n".join([
        f"- {r.payload['title']} (score: {r.payload['score']}) {r.payload.get('url', '')}"
        for r in results
    ])

    prompt = f"""You are a HackerNews assistant. Answer based ONLY on these stories:

{context}

Question: {question}
Answer:"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content


# ── A2A endpoint — reçoit les tâches des autres agents ───────────────────────
@app.post("/tasks/send")
async def tasks_send(task: Task):
    # Extraire la question du format A2A
    question = task.message.parts[0].text

    # Appeler le RAG
    answer = search_and_answer(question)

    # Retourner la réponse au format A2A
    return {
        "id": task.id,
        "status": "completed",
        "result": {
            "role": "agent",
            "parts": [{"text": answer}]
        }
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)