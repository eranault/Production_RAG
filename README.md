# HackerNews RAG — Production Data Platform

> A production-grade, real-time Retrieval-Augmented Generation platform that ingests HackerNews data, indexes it semantically, and exposes an AI-powered query engine with full observability, MCP tool integration, and A2A multi-agent interoperability.

---

## Architecture

```
HackerNews API
      │
      ▼
hackernews.py          ← Async crawler (httpx + APScheduler)
      │
      ▼
MongoDB (replica set)  ← Single source of truth
      │
      ▼ (CDC via Debezium — watches oplog automatically)
Kafka: dbz.hackernews.stories
      │
      ▼
spark_processor.py     ← Unwraps Debezium envelope, cleans HTML
      │
      ▼
Kafka: hackernews-processed
      │
      ├──────────────────────────────────┐
      ▼                                  ▼
mongo_consumer.py              qdrant_indexer.py
(cleaned stories → MongoDB)   (embeddings → Qdrant)
                                         │
                                         ▼
                               rag_query.py (FastAPI)
                               ├── /query        ← RAG endpoint
                               ├── /health       ← Health check
                               └── /metrics      ← Prometheus scrape

mcp_server.py          ← MCP tool (any compatible AI agent)
a2a_server.py          ← A2A agent (multi-agent interoperability)
evaluate_rag.py        ← RAGAS evaluation (faithfulness, relevancy)
```

---

## Stack

| Layer | Technology | Why |
|---|---|---|
| Crawler | Python + httpx + asyncio | Concurrent fetching (17s → 1.5s for 20 stories) |
| Database | MongoDB (replica set) | Required for oplog / CDC |
| CDC | Debezium | Captures every insert/update/delete automatically |
| Message bus | Apache Kafka | Decouples services, enables replay |
| Stream processing | Apache Spark | Distributed DataFrame cleaning at scale |
| Vector database | Qdrant | Open-source, Rust-based, fast cosine similarity |
| Embeddings | all-MiniLM-L6-v2 | 384-dim, CPU-friendly, high quality |
| LLM | LLaMA 3.1 via Groq | Free, fast (LPU hardware), open-source |
| API | FastAPI + uvicorn | Async, auto-docs, production-ready |
| MCP | FastMCP | Exposes RAG as a tool for any AI agent |
| A2A | Custom FastAPI | Agent-to-agent interoperability (Google standard) |
| LLM tracing | LangSmith | Full prompt/response/latency visibility |
| Monitoring | Prometheus + Grafana | Real-time pipeline metrics and dashboards |
| RAG evaluation | RAGAS | Automated faithfulness + relevancy scoring |
| Infrastructure | Docker Compose | One-command setup for all services |

---

## RAG Quality Metrics

Evaluated on 3 test queries using RAGAS with LLaMA 3.1 as judge:

| Metric | Score |
|---|---|
| Faithfulness | **0.95** — 95% of claims grounded in retrieved stories |
| Answer Relevancy | **0.84** — 84% of answers directly address the question |

---

## Services & Ports

| Service | URL |
|---|---|
| FastAPI RAG endpoint | http://localhost:8001/docs |
| MCP Server | stdio (via `mcp dev mcp_server.py`) |
| A2A Server | http://localhost:8002 |
| A2A Agent Card | http://localhost:8002/.well-known/agent.json |
| Qdrant dashboard | http://localhost:6333/dashboard |
| Grafana | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Spark master | http://localhost:8080 |
| Kafka Connect | http://localhost:8083 |

---

## Quickstart

### 1. Prerequisites

- Docker Desktop
- Python 3.11+
- Java 17 (for Spark)
- Node.js LTS (for MCP Inspector)

### 2. Environment variables

Create a `.env` file:

```env
MONGODB_URL=mongodb://localhost:27017/?replicaSet=rs0
GROQ_API_KEY=your_groq_api_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key
LANGCHAIN_PROJECT=hackernews-rag
```

### 3. Start infrastructure

```bash
docker-compose up -d
```

This starts: MongoDB replica set, Kafka, Zookeeper, Spark, Debezium, Qdrant, Prometheus, Grafana.

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Register the Debezium connector

```bash
python register_connector.py
```

### 6. Run the pipeline (4 terminals)

```bash
# Terminal 1 — Crawler
python hackernews.py

# Terminal 2 — Spark processor
python spark_processor.py

# Terminal 3 — MongoDB consumer
python mongo_consumer.py

# Terminal 4 — Qdrant indexer
python qdrant_indexer.py
```

### 7. Start the RAG API

```bash
python rag_query.py
# → http://localhost:8001/docs
```

### 8. Start MCP server

```bash
mcp dev mcp_server.py
```

### 9. Start A2A server

```bash
python a2a_server.py
# → http://localhost:8002/docs
```

---

## Key Design Decisions

**CDC over dual-write:** The crawler writes only to MongoDB. Debezium watches the oplog and automatically publishes every change to Kafka — including updates from external processes, score changes, and deletions. This eliminates the dual-write consistency problem.

**Local replica set over Atlas:** MongoDB CDC requires an oplog, which only exists on replica sets. Running locally gives full CDC capability without cloud costs or network latency.

**MCP + A2A:** MCP exposes the RAG system as a tool consumable by any MCP-compatible agent (Claude, Cursor, etc.). A2A implements Google's agent interoperability standard, enabling this agent to participate in multi-agent orchestration pipelines.

**Groq over OpenAI:** LLaMA 3.1 on Groq's LPU hardware delivers ~10x faster inference than OpenAI at zero cost, making it ideal for a real-time RAG query engine.

---

## Project Structure

```
├── hackernews.py          # Async HackerNews crawler
├── spark_processor.py     # Spark stream: Debezium → cleaned Kafka
├── mongo_consumer.py      # Kafka consumer → MongoDB
├── qdrant_indexer.py      # Kafka consumer → Qdrant vectors
├── rag_query.py           # FastAPI RAG query engine
├── mcp_server.py          # MCP tool server
├── a2a_server.py          # A2A agent server
├── evaluate_rag.py        # RAGAS evaluation script
├── register_connector.py  # Debezium connector setup
├── docker-compose.yml     # Full infrastructure
├── prometheus.yml         # Prometheus scrape config
└── .env                   # Secrets (not committed)
```

---

## Observability

**LangSmith** — every LLM call is traced with full prompt, retrieved context, response, latency, and cost. Accessible at https://smith.langchain.com.

**Prometheus** — scrapes `/metrics` from the FastAPI server every 15 seconds. Tracks `rag_queries_total` (counter) and `rag_query_duration_seconds` (P95 histogram).

**Grafana** — real-time dashboard showing total queries and P95 latency. Data source: `http://prometheus:9090`.

---

## Evaluation

```bash
python evaluate_rag.py
# Output: {'faithfulness': 0.9487, 'answer_relevancy': 0.8388}
```
