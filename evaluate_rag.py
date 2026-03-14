from ragas import evaluate
# Go back to the original import path — these are pre-configured singleton instances
# that accept LangchainLLMWrapper, unlike the new collections classes which only
# work with RAGAS's own InstructorLLM (OpenAI/Google only for now).
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import HuggingFaceEmbeddings as RagasHFEmbeddings
from langchain_groq import ChatGroq
from datasets import Dataset
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
from langchain_huggingface import HuggingFaceEmbeddings
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

model = SentenceTransformer('all-MiniLM-L6-v2')
qdrant = QdrantClient(host="localhost", port=6333)
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

evaluator_llm = LangchainLLMWrapper(ChatGroq(
    api_key=os.getenv("GROQ_API_KEY"),
    model="llama-3.1-8b-instant"
))

evaluator_embeddings = HuggingFaceEmbeddings(
    model="sentence-transformers/all-MiniLM-L6-v2"
)

# No metric instantiation needed here — the old-style metrics are already
# configured singleton objects, not classes you need to construct yourself.
# We'll inject the llm and embeddings via the evaluate() call below instead.


def search_stories(query: str, top_k: int = 5):
    query_embedding = model.encode(query).tolist()
    result = qdrant.query_points(
        collection_name="hackernews",
        query=query_embedding,
        limit=top_k
    )
    return result.points


def ask_with_contexts(question: str):
    results = search_stories(question)
    if not results:
        return "Sorry, I couldn't find any relevant stories.", []

    context_list = [
        f"- {r.payload['title']} (score: {r.payload['score']}) {r.payload.get('url', '')}"
        for r in results
    ]
    context = "\n".join(context_list)

    prompt = f"""You are a HackerNews assistant. Answer the user's question based ONLY on the following stories retrieved from HackerNews. Do not use outside knowledge.

Retrieved stories:
{context}

User question: {question}

Answer:"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content, context_list


test_questions = [
    "What are people saying about artificial intelligence?",
    "Are there any stories about programming or software development?",
    "What are the most interesting tech stories today?",
]

questions, answers, contexts = [], [], []

for question in test_questions:
    answer, context = ask_with_contexts(question)
    questions.append(question)
    answers.append(answer)
    contexts.append(context)

dataset = Dataset.from_dict({
    "question": questions,
    "answer": answers,
    "contexts": contexts,
})

# With the old-style metrics, llm and embeddings are injected here at evaluation
# time rather than at construction time — this is the API they were designed for.
result = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy],
    llm=evaluator_llm,
    embeddings=evaluator_embeddings,
)

print(result)