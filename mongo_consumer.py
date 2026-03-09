import json
import asyncio
from confluent_kafka import Consumer
from dotenv import load_dotenv
from hackernews import save_to_mongodb

load_dotenv()

consumer = Consumer({
    'bootstrap.servers': 'localhost:9092',
    'group.id': 'mongo-consumer',
    'auto.offset.reset': 'earliest'
})
consumer.subscribe(['hackernews-processed'])

async def main():
    while True:
        msg = consumer.poll(1.0)  # wait 1 second for a message
        if msg is None:
            continue
        story = json.loads(msg.value())
        await save_to_mongodb([story])

asyncio.run(main())