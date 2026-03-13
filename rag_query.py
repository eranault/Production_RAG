from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from fastapi import FastAPI
import uvicorn
from pydantic import BaseModel
from langsmith import traceable
from prometheus_client import Counter, Histogram, make_asgi_app
import time

from dotenv import load_dotenv
import os

load_dotenv()
app = FastAPI()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

model = SentenceTransformer('all-MiniLM-L6-v2')
qdrant = QdrantClient(host="localhost", port=6333)

# user's query to neural network, which outputs a numpy array of 384 floats. 
# .tolist() to convert it to a plain Python list, because that's the format Qdrant's client expects.

#we use the same model as in the indexer to make sure the embeddings are in the same vector space, which is crucial for similarity search to work well.
# also we use the same distance metric in the collection config and in the search (cosine here)

def search_stories(query: str, top_k: int = 5):
    query_embedding = model.encode(query).tolist()
    

    result = qdrant.query_points(
        collection_name="hackernews",
        query=query_embedding,   
        limit=top_k              
    )
    
    return result.points  # the actual list of ScoredPoint objects

@traceable(name="hackernews-rag-query")
def ask(question : str) -> str: 
    results = search_stories(question)
    if not results:
        return "Sorry, I couldn't find any relevant stories."
    context = "\n".join([
        f"- {r.payload['title']} (score: {r.payload['score']}) {r.payload.get('url', '')}"
        for r in results
    ])
    prompt = f"""You are a HackerNews assistant. Answer the user's question based ONLY on the following stories retrieved from HackerNews. Do not use outside knowledge.

Retrieved stories:
{context}

User question: {question}

Answer:"""
    
    # Step 4: call Groq with LLaMA 3
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",  # fast, free, and capable enough for our use case
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content



class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    question: str
    answer: str

query_counter = Counter(
    'rag_queries_total', 
    'Total number of RAG queries received'
)

query_latency = Histogram(
    'rag_query_duration_seconds',
    'Time spent processing RAG queries',
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


#@app.post("/query", response_model=QueryResponse)
#async def query_endpoint(request: QueryRequest):
#    answer = ask(request.question)
#    return QueryResponse(question=request.question, answer=answer)


@app.post("/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest):
    # Increment the counter every time someone makes a query
    query_counter.inc()
    
    # Record how long the query takes using the histogram
    # The 'with' block automatically measures start and end time
    with query_latency.time():
        answer = ask(request.question)
    
    return QueryResponse(question=request.question, answer=answer)


@app.get("/health")
async def health(): 
    return{"status" : "ok"}




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
