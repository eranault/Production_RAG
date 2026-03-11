import json
import asyncio
from confluent_kafka import Consumer
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from sentence_transformers import SentenceTransformer

load_dotenv()

# Initialize the embedding model
# all-MiniLM-L6-v2 produces vectors of 384 dimensions
model = SentenceTransformer('all-MiniLM-L6-v2')

# Connect to Qdrant running on localhost
qdrant = QdrantClient(host="localhost", port=6333)

# Create a collection in Qdrant to store our story vectors
# Think of a collection like a table in a regular database
# size=384 because our model produces 384-dimensional vectors
# Distance.COSINE means we measure similarity by the angle between vectors
qdrant.recreate_collection(
    collection_name="hackernews",
    vectors_config=VectorParams(size=384, distance=Distance.COSINE)
)

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'qdrant-indexer',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['hackernews-processed'])

# For each message:
# 1. Parse the JSON
# 2. Create the text to embed (combine title and text if available)
# 3. Generate the embedding using model.encode()
# 4. Store in Qdrant using qdrant.upsert()

while True:
    msg = consumer.poll(1.0)  # wait 1 second for a message
    if msg is None:
        continue
    story = json.loads(msg.value())
    
    # Create the text to embed (combine title and text if available)
    text_to_embed = (story.get('title', '') + ' ' + story.get('text', '')).strip()
    
    # Generate the embedding using model.encode()
    embedding = model.encode(text_to_embed).tolist()  # convert to list for JSON serialization
    
    # Store in Qdrant using qdrant.upsert()
    point = PointStruct(
        id=story['id'],  # use the story ID as the point ID
        vector=embedding,
        payload={
            'title': story.get('title'),
            'url': story.get('url'),
            'score': story.get('score')
        }
    )
    
    qdrant.upsert(collection_name="hackernews", points=[point])

# For each message:
# 1. Parse the JSON
# 2. Create the text to embed (combine title and text if available)
# 3. Generate the embedding using model.encode()
# 4. Store in Qdrant using qdrant.upsert()