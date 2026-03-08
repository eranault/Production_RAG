import csv
import os
import asyncio
import httpx
import motor.motor_asyncio
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from confluent_kafka import Producer
import json

load_dotenv()

async def fetch_item(client, id):
    try:
        response = await client.get(f'https://hacker-news.firebaseio.com/v0/item/{id}.json')
        return response.json()
    except Exception as e:
        print(f"Error fetching item {id}: {e}")
        return None

async def get_stories():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://hacker-news.firebaseio.com/v0/topstories.json")
            story_ids = response.json()[:20]
            stories = await asyncio.gather(*[fetch_item(client, id) for id in story_ids])
            return stories
    except Exception as e:
        print(f"Error fetching stories: {e}")
        return []

async def save_to_mongodb(stories):
    try:
        client = motor.motor_asyncio.AsyncIOMotorClient(os.getenv("MONGODB_URL"))
        db = client['hackernews']
        collection = db['stories']
        for story in stories:
            if story is None:
                continue
            await collection.update_one({'id': story.get('id')}, {'$set': story}, upsert=True)
    except Exception as e:
        print(f"Error saving to MongoDB: {e}")

producer = Producer({'bootstrap.servers': 'localhost:9092'})

async def crawl():
    print("Crawling...")
    stories = await get_stories()
    for story in stories : 
        if story is not None:
            producer.produce('hackernews-stories', value=(json.dumps(story)))
            producer.flush()
    
    await save_to_mongodb(stories)
    print(f"Done — saved {len([s for s in stories if s])} stories")

async def main():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(crawl, 'interval', minutes=5)
    scheduler.start()
    await crawl()  # run once immediately on startup
    await asyncio.Event().wait()  # keep running forever

asyncio.run(main())