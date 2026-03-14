from mcp.server.fastmcp import FastMCP
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from groq import Groq
from dotenv import load_dotenv 
import os

load_dotenv()

mcp = FastMCP ("hackernews-rag")

model = SentenceTransformer('all-MiniLM-L6-v2')
qdrant = QdrantClient(host="localhost", port=6333)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


@mcp.tool()
def search_hackernews(query: str, top_k: int = 5):
    """Search HackerNews stories using semantic search and return an AI-generated answer.
    
    Args:
        query: The user's question about HackerNews stories
        top_k: Number of stories to retrieve (default 5)
    """

    query_embedding = model.encode(query).tolist()
    result = qdrant.query_points(
        collection_name="hackernews",
        query=query_embedding,
        limit=top_k
    )
    results = result.points

    if not results:
        return "Sorry, I couldn't find any relevant stories."
    context = "\n".join([
        f"- {r.payload['title']} (score: {r.payload['score']}) {r.payload.get('url', '')}"
        for r in results
    ])
    prompt = f"""You are a HackerNews assistant. Answer the user's question based ONLY on the following stories retrieved from HackerNews. Do not use outside knowledge.

Retrieved stories:
{context}

User question: {query}

Answer:"""
    
    # Step 4: call Groq with LLaMA 3
    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",  # fast, free, and capable enough for our use case
        messages=[{"role": "user", "content": prompt}]
    )


    return response.choices[0].message.content



if __name__ == "__main__":
    mcp.run()